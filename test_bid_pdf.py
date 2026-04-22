"""Quick test: generate a bid PDF using sample data (no Odoo connection needed)."""
import sys
sys.path.insert(0, ".")
from bid_pdf_generator import build_html
from xhtml2pdf import pisa

# Sample data matching what we'd get from Odoo
order = {
    "name": "S00081",
    "partner_id": [90, "Bidding GCs"],
    "amount_total": 9.70,
    "amount_untaxed": 9.00,
    "amount_tax": 0.70,
    "date_order": "2025-04-25 18:22:52",
    "validity_date": "2025-06-24",
    "state": "sale",
    "user_id": [2, "Carter Janish"],
}

lines = [
    {"name": "Panel (contract Submittals/milestone)\nSign Types Approval Process", "product_id": [450, "Panel"], "product_uom_qty": 1, "price_unit": 1.00, "price_subtotal": 1.00, "sequence": 10},
    {"name": "Panel/ADA Signage", "product_id": False, "product_uom_qty": 0, "price_unit": 0, "price_subtotal": 0, "sequence": 20},
    {"name": "Panel, 8x8\nSign Type A", "product_id": [456, "Panel, 8x8"], "product_uom_qty": 5, "price_unit": 1.00, "price_subtotal": 5.00, "sequence": 30},
    {"name": "Panel, 8x8\nSign Type B", "product_id": [456, "Panel, 8x8"], "product_uom_qty": 3, "price_unit": 1.00, "price_subtotal": 3.00, "sequence": 40},
]

partner = {
    "name": "Best of the Best GC",
    "street": "123 Main St",
    "city": "Oklahoma City",
    "state_id": [39, "Oklahoma (US)"],
    "zip": "73170",
    "phone": "(405) 555-0100",
    "email": "contact@bestgc.com",
}

company = {
    "name": "Patriot ADA Signs",
    "street": "12601 S. Riverview Rd",
    "city": "Oklahoma City",
    "state_id": [39, "Oklahoma (US)"],
    "phone": "+1 405-283-4647",
    "email": "sales@omegasignsco.com",
    "website": "patriotadasigns.com",
}

html = build_html(order, lines, partner, company)

# Save HTML for inspection  
with open("BID_S00081_TEST.html", "w", encoding="utf-8") as f:
    f.write(html)
print("HTML saved → BID_S00081_TEST.html")

# Generate PDF
with open("BID_S00081_TEST.pdf", "wb") as f:
    status = pisa.CreatePDF(html, dest=f)
    if status.err:
        print(f"PDF errors: {status.err}")
    else:
        print("PDF saved → BID_S00081_TEST.pdf")
