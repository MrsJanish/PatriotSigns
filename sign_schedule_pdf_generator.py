#!/usr/bin/env python3
"""
Sign Schedule PDF Generator for Omega Signs Co.

Pulls install instance data from Odoo via XML-RPC and generates a professional
sign schedule PDF matching the Omega Signs format.

Usage:
    python sign_schedule_pdf_generator.py --project-alias 100      # By project alias ID
    python sign_schedule_pdf_generator.py --project-alias 99 100   # Multiple aliases
    python sign_schedule_pdf_generator.py --project-alias 100 --output schedule.pdf
    python sign_schedule_pdf_generator.py --project-alias 100 --upload  # Attach to Odoo

Environment Variables:
    ODOO_URL      - Odoo instance URL
    ODOO_DB       - Odoo database name
    ODOO_USER     - Odoo username
    ODOO_PASSWORD - Odoo password/API key

Requirements:
    pip install xhtml2pdf
"""

import os
import sys
import argparse
import base64
import xmlrpc.client
from datetime import datetime
from collections import OrderedDict
from io import BytesIO

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

COMPANY = {
    "name": "Omega Signs Co.",
    "phone": "+1 405-283-4647",
    "email": "info@omegasignsco.com",
    "website": "omegasignsco.com",
}

# Sign category abbreviation key (full names)
SIGN_CATEGORY_KEY = OrderedDict([
    ("DCAS", "Dimensional-Cast"),
    ("DCHA", "Dimensional-Channel"),
    ("DCUT", "Dimensional-Cut"),
    ("DIG",  "Digital Signage"),
    ("ETCH", "Etched"),
    ("FAB",  "Fabricated Sign"),
    ("FILM", "Blackout Film"),
    ("FOAM", "Dimensional-Foam"),
    ("PAN",  "Panel/ADA/Wayfinding"),
    ("PLQ",  "Cast Plaque"),
    ("POST", "Post & Panel"),
    ("TAG",  "Door/Room Tags"),
    ("TEMP", "Paint Template"),
    ("VIN",  "Vinyl-Letters & Graphics"),
])

# Max data rows per page (excluding header)
ROWS_PER_PAGE = 26


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

    def get_install_instances(self, project_alias_ids: list) -> list:
        """Fetch all install instances for given project alias IDs."""
        return self.call("x_install_instance", "search_read",
            [["x_studio_project_alias", "in", project_alias_ids]],
            fields=[
                "x_name", "x_studio_sign_seq_number",
                "x_studio_sign_type_label", "x_studio_sign_type_letters",
                "x_studio_sign_type_dimensions",
                "x_studio_needs_backer",
                "x_studio_arch_rm_num", "x_studio_arch_rm_name",
                "x_studio_copy_line_1", "x_studio_copy_line_2",
                "x_studio_copy_line_3", "x_studio_copy_line_4",
                "x_studio_copy_line_5",
                "x_studio_remarks",
                "x_studio_sign_category",
                "x_studio_parent_location_display",
                "x_studio_project_alias",
            ],
            order="x_studio_sign_seq_number asc",
            limit=0,
        )

    def get_project_alias(self, alias_id: int) -> dict:
        """Fetch a project alias record."""
        aliases = self.call("x_project_aliases", "search_read",
            [["id", "=", alias_id]],
            fields=["x_name", "display_name", "x_studio_project"],
            limit=1,
        )
        return aliases[0] if aliases else {}

    def get_lead(self, lead_id: int) -> dict:
        """Fetch CRM lead / opportunity."""
        leads = self.call("crm.lead", "search_read",
            [["id", "=", lead_id]],
            fields=["name", "partner_id", "x_studio_project_aliases",
                     "user_id", "contact_name"],
            limit=1,
        )
        return leads[0] if leads else {}

    def get_partner(self, partner_id: int) -> dict:
        partners = self.call("res.partner", "search_read",
            [["id", "=", partner_id]],
            fields=["name", "email", "phone"],
            limit=1,
        )
        return partners[0] if partners else {}

    def get_user(self, user_id: int) -> dict:
        users = self.call("res.users", "search_read",
            [["id", "=", user_id]],
            fields=["name", "email"],
            limit=1,
        )
        return users[0] if users else {}

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
# Data Processing
# ---------------------------------------------------------------------------

def extract_sign_type_letter(label: str) -> str:
    """Extract the letter code from a sign type label like 'A | Room Num/Name'."""
    if not label:
        return ""
    parts = label.split("|")
    return parts[0].strip() if parts else label.strip()


def extract_sign_type_desc(label: str) -> str:
    """Extract the description from a sign type label like 'A | Room Num/Name'."""
    if not label:
        return ""
    parts = label.split("|", 1)
    return parts[1].strip() if len(parts) > 1 else ""


def extract_area(parent_location_display: str) -> str:
    """Extract area code (MS/HS) from 'MS | LVL 1' style strings."""
    if not parent_location_display:
        return ""
    parts = parent_location_display.split("|")
    return parts[0].strip() if parts else ""


def compute_sign_counts(instances: list) -> list:
    """Aggregate sign type counts for the cover page summary table."""
    # Group by sign category + sign type letter
    type_groups = OrderedDict()
    category_counts = OrderedDict()

    for inst in instances:
        cat = inst.get("x_studio_sign_category")
        cat_name = cat[1] if isinstance(cat, list) else (cat or "")
        type_letter = extract_sign_type_letter(inst.get("x_studio_sign_type_label", ""))
        type_desc = extract_sign_type_desc(inst.get("x_studio_sign_type_label", ""))
        dimensions = inst.get("x_studio_sign_type_dimensions", "") or ""
        needs_backer = inst.get("x_studio_needs_backer", False)

        key = (cat_name, type_letter)
        if key not in type_groups:
            type_groups[key] = {
                "sign_cat": cat_name,
                "type_letter": type_letter,
                "type_desc": type_desc,
                "dimensions": dimensions,
                "qty": 0,
                "backer_qty": 0,
            }
        type_groups[key]["qty"] += 1
        if needs_backer:
            type_groups[key]["backer_qty"] += 1

        # Category totals
        if cat_name not in category_counts:
            category_counts[cat_name] = 0
        category_counts[cat_name] += 1

    return list(type_groups.values()), category_counts


def val(v):
    """Return empty string for falsy/False Odoo values."""
    if v is False or v is None:
        return ""
    return str(v)


# ---------------------------------------------------------------------------
# HTML Template
# ---------------------------------------------------------------------------

def build_cover_page_html(
    project_name: str,
    printed_for: str,
    created_on: str,
    print_date: str,
    revision_no: str,
    last_revised: str,
    schedule_by_name: str,
    schedule_by_email: str,
    type_counts: list,
    category_counts: dict,
    used_categories: set,
) -> str:
    """Build the cover page (Page 1) HTML."""

    # Sign Types & Counts table rows
    count_rows = ""
    for tc in type_counts:
        count_rows += f"""
        <tr>
            <td class="center">{tc['sign_cat']}</td>
            <td class="center">{tc['qty']}</td>
            <td class="center bold">{tc['type_letter']}</td>
            <td>{tc['type_desc']}</td>
            <td class="center">{tc['dimensions']}</td>
            <td></td>
            <td></td>
        </tr>"""

    total_count = sum(tc['qty'] for tc in type_counts)

    # Category counts table (right side)
    cat_rows = ""
    for cat_name, count in sorted(category_counts.items()):
        cat_rows += f"""
        <tr>
            <td>{cat_name}</td>
            <td class="center">{count}</td>
            <td></td>
        </tr>"""

    # Backer totals
    total_backers = sum(tc['backer_qty'] for tc in type_counts)
    backer_rows = ""
    for tc in type_counts:
        if tc['backer_qty'] > 0:
            backer_rows += f"""
        <tr>
            <td>{tc['sign_cat']}</td>
            <td class="center">{tc['backer_qty']}</td>
        </tr>"""

    # Abbreviation key (only show categories actually used)
    abbrev_html = ""
    for abbr, full_name in SIGN_CATEGORY_KEY.items():
        css_class = "" if abbr in used_categories else ' style="color:#999;"'
        abbrev_html += f"""
        <tr{css_class}>
            <td class="abbr-code">{abbr}</td>
            <td>{full_name}</td>
        </tr>"""

    return f"""
    <!-- ===== COVER PAGE ===== -->
    <div class="cover-page">
        <!-- Header -->
        <table class="layout header-table">
            <tr>
                <td style="width:55%;">
                    <div class="title-bar">SIGN SCHEDULE</div>
                    <div class="company-name">OMEGA SIGNS</div>
                    <div class="project-name">{project_name}</div>
                </td>
                <td style="width:45%; text-align:right; vertical-align:top;">
                    <table class="meta-table">
                        <tr><td class="meta-label">Schedule by:</td><td class="meta-value">{schedule_by_name}</td></tr>
                        <tr><td></td><td class="meta-value" style="font-size:7pt;">{schedule_by_email}</td></tr>
                        <tr><td class="meta-label">Printed for:</td><td class="meta-value">{printed_for}</td></tr>
                        <tr><td class="meta-label">Created on:</td><td class="meta-value">{created_on}</td></tr>
                        <tr><td class="meta-label">Print Date:</td><td class="meta-value">{print_date}</td></tr>
                        <tr><td class="meta-label">Revision No:</td><td class="meta-value">{revision_no}</td></tr>
                        <tr><td class="meta-label">Last Revised:</td><td class="meta-value">{last_revised}</td></tr>
                    </table>
                </td>
            </tr>
        </table>

        <!-- Sign Types & Counts -->
        <table class="layout" style="margin-top:8pt;">
            <tr>
                <td style="width:65%; vertical-align:top; padding-right:8pt;">
                    <div class="section-header">SIGN TYPES &amp; COUNTS</div>
                    <table class="data-table counts-table">
                        <thead>
                            <tr>
                                <th style="width:50pt;">Sign Cat</th>
                                <th style="width:30pt;">Qty</th>
                                <th style="width:40pt;">Sign Type Backer Qty</th>
                                <th>Sign Type Description</th>
                                <th style="width:55pt;">Dimensions</th>
                                <th style="width:40pt;">Notes</th>
                                <th style="width:40pt;">Note2</th>
                            </tr>
                        </thead>
                        <tbody>
                            {count_rows}
                            <tr class="total-row">
                                <td></td>
                                <td class="center bold">{total_count}</td>
                                <td colspan="5"></td>
                            </tr>
                        </tbody>
                    </table>
                </td>
                <td style="width:35%; vertical-align:top;">
                    <div class="section-header">SIGN CATEGORY COUNTS</div>
                    <table class="data-table cat-counts-table">
                        <thead>
                            <tr>
                                <th>Sign Categories</th>
                                <th style="width:55pt;">Sign Cat Total Count</th>
                                <th style="width:60pt;">Approval Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {cat_rows}
                        </tbody>
                    </table>

                    <!-- Backer note -->
                    <p class="backer-note">* Panel Backer totals per Sign Type are shown in "Backers" column in Counts section</p>
                </td>
            </tr>
        </table>

        <!-- Abbreviation Key -->
        <div class="section-header" style="margin-top:10pt;">SIGN CATEGORY ABBREVIATION KEY</div>
        <table class="abbrev-table">
            <tbody>
                {abbrev_html}
            </tbody>
        </table>

        <p class="important-notice">IMPORTANT: ONLY SIGN TYPES SHOWN ON THIS OFFICIAL SIGN SCHEDULE WILL BE PRODUCED. PLEASE ENSURE ALL APPROVED ARE ACCURATELY LISTED.</p>
    </div>
    """


def build_data_page_html(
    rows: list,
    page_num: int,
    total_pages: int,
    project_name: str,
    print_date: str,
    fill_blank_rows: bool = False,
    is_supplementary: bool = False,
) -> str:
    """Build one data page of the sign schedule table."""

    # Header instruction text
    instruction = 'INSTRUCTIONS: 1) LOCATION (per plans) "To Rm" for installer reference, not copy; 1) COPY exact sign copy'

    rows_html = ""
    row_count = len(rows)

    for row in rows:
        sign_num = val(row.get("sign_num", ""))
        sign_type = val(row.get("sign_type", ""))
        needs_backer = "Y" if row.get("needs_backer") else ""
        rm_num = val(row.get("rm_num", ""))
        rm_name = val(row.get("rm_name", ""))
        cl1 = val(row.get("copy_line_1", ""))
        cl2 = val(row.get("copy_line_2", ""))
        cl3 = val(row.get("copy_line_3", ""))
        cl4 = val(row.get("copy_line_4", ""))
        cl5 = val(row.get("copy_line_5", ""))
        remarks = val(row.get("remarks", ""))

        rows_html += f"""
            <tr>
                <td class="center vcenter">{sign_num}</td>
                <td class="center vcenter bold">{sign_type}</td>
                <td class="center vcenter">{needs_backer}</td>
                <td class="center vcenter">{rm_num}</td>
                <td class="vcenter">{rm_name}</td>
                <td class="vcenter">{cl1}</td>
                <td class="vcenter">{cl2}</td>
                <td class="vcenter">{cl3}</td>
                <td class="vcenter">{cl4}</td>
                <td class="vcenter">{cl5}</td>
                <td class="vcenter">{remarks}</td>
            </tr>"""

    # Fill remaining rows with blanks
    if fill_blank_rows or is_supplementary:
        fill_count = ROWS_PER_PAGE if is_supplementary else (ROWS_PER_PAGE - row_count)
        for _ in range(max(0, fill_count)):
            rows_html += """
            <tr>
                <td class="center vcenter">&nbsp;</td>
                <td class="center vcenter">&nbsp;</td>
                <td class="center vcenter">&nbsp;</td>
                <td class="center vcenter">&nbsp;</td>
                <td class="vcenter">&nbsp;</td>
                <td class="vcenter">&nbsp;</td>
                <td class="vcenter">&nbsp;</td>
                <td class="vcenter">&nbsp;</td>
                <td class="vcenter">&nbsp;</td>
                <td class="vcenter">&nbsp;</td>
                <td class="vcenter">&nbsp;</td>
            </tr>"""

    supplementary_label = " — SUPPLEMENTARY SHEET" if is_supplementary else ""
    file_label = f"{project_name} - Official Sign Schedule{supplementary_label}"

    return f"""
    <div class="data-page">
        <div class="data-page-header">
            <div class="instruction-text">{instruction}</div>
            <table class="layout">
                <tr>
                    <td>{file_label}</td>
                    <td style="text-align:right;">{print_date}</td>
                </tr>
            </table>
        </div>

        <table class="data-table schedule-table">
            <thead>
                <tr>
                    <th style="width:42pt;">Area / Sign #</th>
                    <th style="width:32pt;">Sign Type</th>
                    <th style="width:32pt;">Needs Backer</th>
                    <th style="width:38pt;">Rm #</th>
                    <th style="width:80pt;">Room Name on Plans</th>
                    <th>Copy Line 1</th>
                    <th>Copy Line 2</th>
                    <th>Copy Line 3</th>
                    <th>Copy Line 4</th>
                    <th>Copy Line 5</th>
                    <th style="width:40pt;">Remarks</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <p class="important-notice">IMPORTANT: ONLY SIGN TYPES SHOWN ON THIS OFFICIAL SIGN SCHEDULE WILL BE PRODUCED. PLEASE ENSURE ALL APPROVED ARE ACCURATELY LISTED.</p>

        <div class="page-footer">
            <span>Omega Signs Co.</span>
            <span class="page-num">Page {page_num} of {total_pages}</span>
        </div>
    </div>
    """


def build_full_html(
    project_name: str,
    printed_for: str,
    created_on: str,
    print_date: str,
    revision_no: str,
    last_revised: str,
    schedule_by_name: str,
    schedule_by_email: str,
    instances: list,
) -> str:
    """Build the complete multi-page sign schedule HTML."""

    # Compute cover page aggregates
    type_counts, category_counts = compute_sign_counts(instances)
    used_categories = set(category_counts.keys())

    # Prepare data rows
    data_rows = []
    for inst in instances:
        sign_num = inst.get("x_studio_sign_seq_number", 0)
        area = extract_area(inst.get("x_studio_parent_location_display", ""))

        data_rows.append({
            "sign_num": sign_num if sign_num else "",
            "sign_type": extract_sign_type_letter(inst.get("x_studio_sign_type_label", "")),
            "needs_backer": inst.get("x_studio_needs_backer", False),
            "rm_num": inst.get("x_studio_arch_rm_num", ""),
            "rm_name": inst.get("x_studio_arch_rm_name", ""),
            "copy_line_1": inst.get("x_studio_copy_line_1", ""),
            "copy_line_2": inst.get("x_studio_copy_line_2", ""),
            "copy_line_3": inst.get("x_studio_copy_line_3", ""),
            "copy_line_4": inst.get("x_studio_copy_line_4", ""),
            "copy_line_5": inst.get("x_studio_copy_line_5", ""),
            "remarks": area or inst.get("x_studio_remarks", ""),
        })

    # Paginate data rows
    pages = []
    for i in range(0, max(len(data_rows), 1), ROWS_PER_PAGE):
        pages.append(data_rows[i:i + ROWS_PER_PAGE])

    # Total pages: 1 cover + N data pages + 1 supplementary
    total_pages = 1 + len(pages) + 1

    # Build cover page
    cover_html = build_cover_page_html(
        project_name=project_name,
        printed_for=printed_for,
        created_on=created_on,
        print_date=print_date,
        revision_no=revision_no,
        last_revised=last_revised,
        schedule_by_name=schedule_by_name,
        schedule_by_email=schedule_by_email,
        type_counts=type_counts,
        category_counts=category_counts,
        used_categories=used_categories,
    )

    # Build data pages
    data_pages_html = ""
    for idx, page_rows in enumerate(pages):
        is_last_data_page = (idx == len(pages) - 1)
        data_pages_html += build_data_page_html(
            rows=page_rows,
            page_num=idx + 2,  # Page 1 is cover
            total_pages=total_pages,
            project_name=project_name,
            print_date=print_date,
            fill_blank_rows=is_last_data_page,
        )

    # Build supplementary blank sheet
    supplementary_html = build_data_page_html(
        rows=[],
        page_num=total_pages,
        total_pages=total_pages,
        project_name=project_name,
        print_date=print_date,
        is_supplementary=True,
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    @page {{
        size: letter landscape;
        margin: 0.35in 0.4in 0.3in 0.4in;
    }}

    body {{
        font-family: Arial, Helvetica, sans-serif;
        font-size: 7.5pt;
        color: #222;
        margin: 0;
        padding: 0;
    }}

    /* Layout helpers */
    table.layout {{
        width: 100%;
        border-collapse: collapse;
    }}
    table.layout td {{
        vertical-align: top;
        padding: 0;
        border: none;
    }}

    /* Cover page */
    .cover-page {{
        page-break-after: always;
    }}
    .title-bar {{
        font-size: 18pt;
        font-weight: bold;
        color: #1a3a5c;
        letter-spacing: 1pt;
    }}
    .company-name {{
        font-size: 14pt;
        font-weight: bold;
        color: #333;
        margin-top: 2pt;
    }}
    .project-name {{
        font-size: 10pt;
        color: #555;
        margin-top: 2pt;
    }}
    .meta-table {{
        border-collapse: collapse;
        font-size: 8pt;
    }}
    .meta-table td {{
        padding: 1pt 4pt;
        border: none;
    }}
    .meta-label {{
        font-weight: bold;
        color: #555;
        text-align: right;
        white-space: nowrap;
    }}
    .meta-value {{
        color: #222;
    }}

    .section-header {{
        font-size: 8pt;
        font-weight: bold;
        color: #1a3a5c;
        background-color: #dce6f0;
        padding: 3pt 6pt;
        margin-bottom: 2pt;
        border: 1px solid #aaa;
    }}

    /* Data tables */
    .data-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 7pt;
    }}
    .data-table thead th {{
        background-color: #dce6f0;
        color: #1a3a5c;
        font-size: 6.5pt;
        font-weight: bold;
        padding: 3pt 3pt;
        border: 1px solid #999;
        text-align: center;
        vertical-align: middle;
    }}
    .data-table tbody td {{
        padding: 2pt 3pt;
        border: 1px solid #bbb;
        font-size: 7pt;
        vertical-align: middle;
    }}
    .data-table .total-row td {{
        font-weight: bold;
        border-top: 2px solid #333;
        background-color: #f0f0f0;
    }}

    /* Schedule table specific */
    .schedule-table tbody td {{
        height: 16pt;
        vertical-align: middle;
    }}

    /* Helpers */
    .center {{ text-align: center; }}
    .bold {{ font-weight: bold; }}
    .vcenter {{ vertical-align: middle; }}

    /* Abbreviation key */
    .abbrev-table {{
        border-collapse: collapse;
        font-size: 7pt;
        margin-top: 4pt;
    }}
    .abbrev-table td {{
        padding: 1pt 4pt;
        border: none;
    }}
    .abbrev-table .abbr-code {{
        font-weight: bold;
        width: 40pt;
        color: #1a3a5c;
    }}

    /* Category counts table */
    .cat-counts-table {{
        font-size: 7pt;
    }}

    /* Important notice */
    .important-notice {{
        font-size: 6.5pt;
        font-weight: bold;
        color: #c00;
        text-align: center;
        margin-top: 4pt;
        padding: 3pt;
        border: 1px solid #c00;
        background-color: #fff8f8;
    }}

    .backer-note {{
        font-size: 6pt;
        color: #666;
        font-style: italic;
        margin-top: 4pt;
    }}

    /* Data pages */
    .data-page {{
        page-break-after: always;
    }}
    .data-page-header {{
        margin-bottom: 4pt;
    }}
    .instruction-text {{
        font-size: 6pt;
        color: #888;
        margin-bottom: 2pt;
    }}

    .page-footer {{
        display: flex;
        justify-content: space-between;
        font-size: 7pt;
        color: #555;
        margin-top: 4pt;
        padding-top: 2pt;
        border-top: 1px solid #ccc;
    }}
    .page-footer .page-num {{
        float: right;
    }}
    .page-footer span:first-child {{
        float: left;
    }}
</style>
</head>
<body>

{cover_html}

{data_pages_html}

{supplementary_html}

</body>
</html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate Sign Schedule PDF from Odoo install instance data"
    )
    parser.add_argument("--project-alias", type=int, nargs="+", required=True,
                        help="Project alias ID(s) to include")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output PDF filename")
    parser.add_argument("--upload", action="store_true",
                        help="Upload generated PDF as attachment to CRM lead in Odoo")
    parser.add_argument("--html", action="store_true",
                        help="Also save the intermediate HTML for debugging")
    parser.add_argument("--printed-for", type=str, default="",
                        help="'Printed for' field on cover page")
    parser.add_argument("--revision", type=str, default="1",
                        help="Revision number")
    args = parser.parse_args()

    # Validate credentials
    if not all([ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD]):
        print("ERROR: Missing ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD env vars")
        sys.exit(1)

    # Connect to Odoo
    print("Connecting to Odoo...")
    odoo = OdooFetcher(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD)

    # Fetch project alias info
    alias_names = []
    lead_id = None
    for alias_id in args.project_alias:
        alias = odoo.get_project_alias(alias_id)
        if alias:
            alias_names.append(alias.get("x_name", f"Alias {alias_id}"))
            project = alias.get("x_studio_project")
            if project and isinstance(project, list) and not lead_id:
                lead_id = project[0]
        else:
            print(f"WARNING: Project alias {alias_id} not found")

    project_name = ", ".join(alias_names) if alias_names else "Sign Schedule"
    print(f"Project: {project_name}")

    # Fetch lead info
    partner_name = ""
    schedule_by_name = "Tiffany Janish"
    schedule_by_email = "tiffany@omegasignsco.com"
    if lead_id:
        lead = odoo.get_lead(lead_id)
        if lead:
            project_name = lead.get("name", project_name)
            if lead.get("partner_id"):
                partner = odoo.get_partner(lead["partner_id"][0])
                partner_name = partner.get("name", "")
            if lead.get("user_id"):
                user = odoo.get_user(lead["user_id"][0])
                if user:
                    schedule_by_name = user.get("name", schedule_by_name)
                    schedule_by_email = user.get("email", schedule_by_email)

    # Fetch install instances
    print(f"Fetching install instances for alias IDs: {args.project_alias}...")
    instances = odoo.get_install_instances(args.project_alias)
    print(f"  → {len(instances)} install instances found")

    if not instances:
        print("WARNING: No install instances found. Generating empty schedule.")

    # Build HTML
    now = datetime.now()
    html_content = build_full_html(
        project_name=project_name,
        printed_for=args.printed_for or partner_name,
        created_on=now.strftime("%-m/%-d/%Y") if os.name != "nt" else now.strftime("%#m/%#d/%Y"),
        print_date=now.strftime("%-m/%-d/%Y") if os.name != "nt" else now.strftime("%#m/%#d/%Y"),
        revision_no=args.revision,
        last_revised=now.strftime("%-m/%-d/%Y") if os.name != "nt" else now.strftime("%#m/%#d/%Y"),
        schedule_by_name=schedule_by_name,
        schedule_by_email=schedule_by_email,
        instances=instances,
    )

    # Save HTML if requested
    if args.html:
        html_file = args.output.replace(".pdf", ".html") if args.output else "sign_schedule.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"  → HTML saved: {html_file}")

    # Generate PDF
    safe_name = project_name.replace(" ", "_").replace("/", "_")[:50]
    output_file = args.output or f"SS_{safe_name}_{now.strftime('%Y%m%d')}.pdf"
    print(f"Generating PDF → {output_file}")

    with open(output_file, "wb") as pdf_file:
        status = pisa.CreatePDF(html_content, dest=pdf_file)
        if status.err:
            print(f"ERROR: PDF generation failed with {status.err} errors")
            sys.exit(1)

    file_size = os.path.getsize(output_file)
    print(f"  ✓ PDF generated: {output_file} ({file_size:,} bytes)")

    # Upload to Odoo
    if args.upload and lead_id:
        with open(output_file, "rb") as f:
            pdf_data = f.read()
        att_id = odoo.upload_attachment("crm.lead", lead_id, output_file, pdf_data)
        print(f"  ✓ Uploaded to Odoo CRM lead #{lead_id} as attachment #{att_id}")
    elif args.upload:
        print("  ⚠ Cannot upload: no CRM lead ID found for these project aliases")

    print("Done!")


if __name__ == "__main__":
    main()
