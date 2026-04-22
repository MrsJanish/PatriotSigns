#!/usr/bin/env python3
"""
Bid PDF Generator for Patriot ADA Signs

Pulls a Sale Order from Odoo via XML-RPC and generates a professional
bid proposal PDF. Uses WeasyPrint for HTML→PDF conversion.

Usage:
    python bid_pdf_generator.py 81                # Generate bid for SO# S00081
    python bid_pdf_generator.py 81 --output bid.pdf
    python bid_pdf_generator.py 81 --upload       # Generate and attach to Odoo record

Environment Variables:
    ODOO_URL      - Odoo instance URL
    ODOO_DB       - Odoo database name
    ODOO_USER     - Odoo username
    ODOO_PASSWORD - Odoo password/API key

Requirements:
    pip install weasyprint
"""

import os
import sys
import argparse
import base64
import xmlrpc.client
from datetime import datetime

try:
    from xhtml2pdf import pisa
except ImportError:
    print("ERROR: 'xhtml2pdf' required. Install with: pip install xhtml2pdf")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ODOO_URL = os.environ.get("ODOO_URL", "")
ODOO_DB = os.environ.get("ODOO_DB", "")
ODOO_USER = os.environ.get("ODOO_USER", "")
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "")

# Company defaults (fallback if Odoo company fetch fails)
COMPANY = {
    "name": "Patriot ADA Signs",
    "street": "12601 S. Riverview Rd",
    "city": "Oklahoma City",
    "state": "OK",
    "zip": "",
    "phone": "+1 405-283-4647",
    "email": "sales@omegasignsco.com",
    "website": "patriotadasigns.com",
}

# ---------------------------------------------------------------------------
# Odoo Data Fetcher
# ---------------------------------------------------------------------------

class OdooFetcher:
    def __init__(self, url, db, user, password):
        self.url = url.rstrip("/")
        self.db = db
        self.user = user
        self.password = password
        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.uid = common.authenticate(db, user, password, {})
        if not self.uid:
            raise RuntimeError("Odoo authentication failed")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def call(self, model, method, *args, **kwargs):
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, method, list(args), kwargs
        )

    def get_sale_order(self, order_id: int) -> dict:
        orders = self.call("sale.order", "search_read",
            [["id", "=", order_id]],
            fields=[
                "name", "partner_id", "amount_total", "amount_untaxed",
                "amount_tax", "date_order", "validity_date", "note",
                "state", "order_line", "user_id",
            ],
            limit=1,
        )
        if not orders:
            raise ValueError(f"Sale order {order_id} not found")
        return orders[0]

    def get_order_lines(self, line_ids: list) -> list:
        return self.call("sale.order.line", "search_read",
            [["id", "in", line_ids]],
            fields=[
                "name", "product_id", "product_uom_qty", "price_unit",
                "price_subtotal", "discount", "sequence",
            ],
        )

    def get_partner(self, partner_id: int) -> dict:
        partners = self.call("res.partner", "search_read",
            [["id", "=", partner_id]],
            fields=[
                "name", "street", "street2", "city", "state_id",
                "zip", "phone", "email", "is_company",
            ],
            limit=1,
        )
        return partners[0] if partners else {}

    def get_company(self) -> dict:
        companies = self.call("res.company", "search_read",
            [],
            fields=["name", "street", "city", "state_id", "phone", "email", "website"],
            limit=1,
        )
        return companies[0] if companies else {}

    def upload_attachment(self, model: str, res_id: int, filename: str, data: bytes):
        return self.call("ir.attachment", "create", {
            "name": filename,
            "type": "binary",
            "datas": base64.b64encode(data).decode(),
            "res_model": model,
            "res_id": res_id,
            "mimetype": "application/pdf",
        })


# ---------------------------------------------------------------------------
# HTML Template
# ---------------------------------------------------------------------------

def build_html(order: dict, lines: list, partner: dict, company: dict) -> str:
    """Build the bid proposal HTML from Odoo data."""

    # Format dates
    order_date = ""
    if order.get("date_order"):
        try:
            dt = datetime.fromisoformat(str(order["date_order"]))
            order_date = dt.strftime("%B %d, %Y")
        except (ValueError, TypeError):
            order_date = str(order["date_order"])[:10]

    validity_date = ""
    if order.get("validity_date"):
        try:
            dt = datetime.fromisoformat(str(order["validity_date"]))
            validity_date = dt.strftime("%B %d, %Y")
        except (ValueError, TypeError):
            validity_date = str(order["validity_date"])[:10]

    # Partner address
    partner_name = partner.get("name", "Customer")
    partner_addr_parts = []
    if partner.get("street"):
        partner_addr_parts.append(partner["street"])
    if partner.get("street2"):
        partner_addr_parts.append(partner["street2"])
    city_state = []
    if partner.get("city"):
        city_state.append(partner["city"])
    if partner.get("state_id"):
        state_name = partner["state_id"][1] if isinstance(partner["state_id"], list) else str(partner["state_id"])
        # Extract abbreviation from "Oklahoma (US)" format
        state_name = state_name.split(" (")[0] if " (" in state_name else state_name
        city_state.append(state_name)
    if city_state:
        line = ", ".join(city_state)
        if partner.get("zip"):
            line += f" {partner['zip']}"
        partner_addr_parts.append(line)
    partner_address = "<br>".join(partner_addr_parts)

    # Company info
    co = {**COMPANY}
    if company:
        co["name"] = company.get("name", co["name"])
        co["street"] = company.get("street", co["street"])
        co["city"] = company.get("city", co["city"])
        if company.get("state_id"):
            state = company["state_id"][1] if isinstance(company["state_id"], list) else str(company["state_id"])
            co["state"] = state.split(" (")[0] if " (" in state else state
        co["phone"] = company.get("phone", co["phone"])
        co["email"] = company.get("email", co["email"])
        co["website"] = company.get("website", co["website"])

    # Build line items HTML
    lines_html = ""
    item_num = 0
    for line in sorted(lines, key=lambda l: l.get("sequence", 0)):
        # Skip section headers (zero-priced lines with no product)
        if not line.get("product_id") and line.get("price_unit", 0) == 0:
            # Render as a section header row
            lines_html += f"""
            <tr class="section-row">
                <td colspan="5"><strong>{line.get('name', '')}</strong></td>
            </tr>"""
            continue

        item_num += 1
        name = line.get("name", "").replace("\n", "<br>")
        qty = line.get("product_uom_qty", 0)
        price = line.get("price_unit", 0)
        subtotal = line.get("price_subtotal", 0)

        # Format as integer if whole number
        qty_display = int(qty) if qty == int(qty) else f"{qty:.1f}"

        lines_html += f"""
            <tr>
                <td class="center">{item_num}</td>
                <td>{name}</td>
                <td class="center">{qty_display}</td>
                <td class="right">${price:,.2f}</td>
                <td class="right">${subtotal:,.2f}</td>
            </tr>"""

    # Salesperson
    salesperson = ""
    if order.get("user_id"):
        salesperson = order["user_id"][1] if isinstance(order["user_id"], list) else str(order["user_id"])

    # Build tax row
    tax_row = ""
    if order.get('amount_tax', 0) > 0:
        tax_row = f"""
        <tr>
            <td style="padding: 5px 10px; border-bottom: 1px solid #eee; font-size: 11px;">Tax</td>
            <td style="padding: 5px 10px; border-bottom: 1px solid #eee; font-size: 11px; text-align: right;">${order.get('amount_tax', 0):,.2f}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    @page {{
        size: letter;
        margin: 0.6in 0.75in;
    }}

    body {{
        font-family: Helvetica, Arial, sans-serif;
        font-size: 11px;
        color: #333333;
    }}

    /* Layout tables have no borders */
    table.layout {{
        width: 100%;
        border-collapse: collapse;
    }}
    table.layout td {{
        vertical-align: top;
        padding: 0;
    }}

    /* Line items table */
    table.items {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        margin-bottom: 10px;
    }}
    table.items thead th {{
        background-color: #f0f3f7;
        color: #1a3a5c;
        font-size: 10px;
        padding: 8px 10px;
        border-bottom: 2px solid #1a3a5c;
        text-align: left;
    }}
    table.items tbody td {{
        padding: 7px 10px;
        border-bottom: 1px solid #eeeeee;
        vertical-align: top;
        font-size: 11px;
    }}
    table.items .section-row td {{
        background-color: #f0f3f7;
        color: #1a3a5c;
        font-size: 10px;
        font-weight: bold;
        padding: 5px 10px;
        border-bottom: 1px solid #dddddd;
    }}

    /* Totals table */
    table.totals {{
        width: 250px;
        border-collapse: collapse;
        margin-left: auto;
    }}
    table.totals td {{
        padding: 5px 10px;
        font-size: 11px;
    }}

    .section-label {{
        font-size: 10px;
        color: #1a3a5c;
        border-bottom: 1px solid #dddddd;
        padding-bottom: 4px;
        margin-bottom: 6px;
        font-weight: bold;
    }}
</style>
</head>
<body>

<!-- ===== HEADER ===== -->
<table class="layout" style="border-bottom: 3px solid #1a3a5c; padding-bottom: 12px; margin-bottom: 20px;">
    <tr>
        <td style="width: 60%;">
            <span style="font-size: 26px; font-weight: bold; color: #1a3a5c;">{co['name']}</span><br/>
            <span style="font-size: 11px; color: #666666;">ADA Compliant Signage Solutions</span>
        </td>
        <td style="width: 40%; text-align: right; font-size: 10px; color: #555555;">
            {co['street']}<br/>
            {co['city']}, {co['state']}<br/>
            {co['phone']}<br/>
            {co['email']}<br/>
            {co['website']}
        </td>
    </tr>
</table>

<!-- ===== TITLE BAR ===== -->
<table class="layout" style="margin-bottom: 20px;">
    <tr>
        <td style="background-color: #1a3a5c; color: white; padding: 10px 20px; font-size: 18px; font-weight: bold; letter-spacing: 2px;">
            BID PROPOSAL
        </td>
    </tr>
</table>

<!-- ===== INFO SECTION ===== -->
<table class="layout" style="margin-bottom: 20px;">
    <tr>
        <td style="width: 50%; padding-right: 20px;">
            <div class="section-label">SUBMITTED TO</div>
            <p>
                <strong>{partner_name}</strong><br/>
                {partner_address if partner_address else ""}
                {"<br/>" + partner.get("phone", "") if partner.get("phone") else ""}
                {"<br/>" + partner.get("email", "") if partner.get("email") else ""}
            </p>
        </td>
        <td style="width: 50%; padding-left: 20px;">
            <div class="section-label">PROPOSAL DETAILS</div>
            <p>
                <strong>Proposal #:</strong> {order['name']}<br/>
                <strong>Date:</strong> {order_date}<br/>
                {"<strong>Valid Until:</strong> " + validity_date + "<br/>" if validity_date else ""}
                {"<strong>Prepared By:</strong> " + salesperson if salesperson else ""}
            </p>
        </td>
    </tr>
</table>

<!-- ===== LINE ITEMS ===== -->
<table class="items">
    <thead>
        <tr>
            <th style="width: 40px; text-align: center;">#</th>
            <th>Description</th>
            <th style="width: 55px; text-align: center;">Qty</th>
            <th style="width: 85px; text-align: right;">Unit Price</th>
            <th style="width: 85px; text-align: right;">Amount</th>
        </tr>
    </thead>
    <tbody>
        {lines_html}
    </tbody>
</table>

<!-- ===== TOTALS ===== -->
<table class="totals">
    <tr>
        <td style="padding: 5px 10px; border-bottom: 1px solid #eeeeee; font-size: 11px;">Subtotal</td>
        <td style="padding: 5px 10px; border-bottom: 1px solid #eeeeee; font-size: 11px; text-align: right;">${order.get('amount_untaxed', 0):,.2f}</td>
    </tr>
    {tax_row}
    <tr>
        <td style="padding: 8px 10px; border-top: 2px solid #1a3a5c; border-bottom: 2px solid #1a3a5c; font-size: 14px; font-weight: bold; color: #1a3a5c;">Total Bid Amount</td>
        <td style="padding: 8px 10px; border-top: 2px solid #1a3a5c; border-bottom: 2px solid #1a3a5c; font-size: 14px; font-weight: bold; color: #1a3a5c; text-align: right;">${order.get('amount_total', 0):,.2f}</td>
    </tr>
</table>

<!-- ===== TERMS ===== -->
<div style="margin-top: 25px; padding-top: 12px; border-top: 1px solid #dddddd;">
    <div class="section-label">TERMS &amp; CONDITIONS</div>
    <ul style="font-size: 10px; color: #555555; padding-left: 18px; line-height: 1.8;">
        <li>All signage manufactured to ADA/TAS compliance standards</li>
        <li>Pricing valid for the duration noted above</li>
        <li>Installation labor included unless otherwise noted</li>
        <li>Payment terms: Net 30 from date of invoice</li>
        <li>Submittals provided for approval prior to fabrication</li>
        <li>Lead time: 4-6 weeks from submittal approval</li>
        <li>This proposal does not include permit fees, engineering, or structural modifications</li>
    </ul>
</div>

<!-- ===== SIGNATURES ===== -->
<table class="layout" style="margin-top: 35px;">
    <tr>
        <td style="width: 45%; padding-right: 30px;">
            <div style="border-bottom: 1px solid #333333; height: 28px;">&nbsp;</div>
            <div style="font-size: 9px; color: #999999; padding-top: 3px;">Authorized Signature &mdash; {co['name']}</div>
        </td>
        <td style="width: 10%;">&nbsp;</td>
        <td style="width: 45%; padding-left: 30px;">
            <div style="border-bottom: 1px solid #333333; height: 28px;">&nbsp;</div>
            <div style="font-size: 9px; color: #999999; padding-top: 3px;">Date</div>
        </td>
    </tr>
</table>

<table class="layout" style="margin-top: 25px;">
    <tr>
        <td style="width: 45%; padding-right: 30px;">
            <div style="border-bottom: 1px solid #333333; height: 28px;">&nbsp;</div>
            <div style="font-size: 9px; color: #999999; padding-top: 3px;">Accepted By &mdash; {partner_name}</div>
        </td>
        <td style="width: 10%;">&nbsp;</td>
        <td style="width: 45%; padding-left: 30px;">
            <div style="border-bottom: 1px solid #333333; height: 28px;">&nbsp;</div>
            <div style="font-size: 9px; color: #999999; padding-top: 3px;">Date</div>
        </td>
    </tr>
</table>

<!-- ===== FOOTER ===== -->
<div style="margin-top: 35px; text-align: center; font-size: 9px; color: #999999; border-top: 1px solid #eeeeee; padding-top: 8px;">
    {co['name']} &bull; {co['street']}, {co['city']}, {co['state']} &bull; {co['phone']} &bull; {co['website']}
</div>

</body>
</html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate bid PDF from Odoo sale order")
    parser.add_argument("order_id", type=int, help="Sale Order ID")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output PDF filename (default: BID_{order_name}.pdf)")
    parser.add_argument("--upload", action="store_true",
                        help="Upload generated PDF as attachment to the sale order in Odoo")
    parser.add_argument("--html", action="store_true",
                        help="Also save the intermediate HTML for debugging")
    args = parser.parse_args()

    # Validate credentials
    if not all([ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD]):
        print("ERROR: Missing ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD env vars")
        sys.exit(1)

    # Fetch data
    print(f"Connecting to Odoo...")
    odoo = OdooFetcher(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD)

    print(f"Fetching sale order {args.order_id}...")
    order = odoo.get_sale_order(args.order_id)
    print(f"  → {order['name']} | {order['partner_id'][1]} | ${order['amount_total']:,.2f}")

    lines = odoo.get_order_lines(order["order_line"])
    print(f"  → {len(lines)} line items")

    partner = odoo.get_partner(order["partner_id"][0])
    company = odoo.get_company()

    # Build HTML
    html_content = build_html(order, lines, partner, company)

    # Save HTML if requested
    if args.html:
        html_file = f"BID_{order['name']}.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"  → HTML saved: {html_file}")

    # Generate PDF
    output_file = args.output or f"BID_{order['name']}.pdf"
    print(f"Generating PDF → {output_file}")
    with open(output_file, "wb") as pdf_file:
        status = pisa.CreatePDF(html_content, dest=pdf_file)
        if status.err:
            print(f"ERROR: PDF generation failed with {status.err} errors")
            sys.exit(1)
    print(f"  ✓ PDF generated: {output_file}")

    # Upload to Odoo
    if args.upload:
        with open(output_file, "rb") as f:
            pdf_data = f.read()
        att_id = odoo.upload_attachment("sale.order", args.order_id, output_file, pdf_data)
        print(f"  ✓ Uploaded to Odoo as attachment #{att_id}")

    print("Done!")


if __name__ == "__main__":
    main()
