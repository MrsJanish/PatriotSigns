from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_panel_sign = fields.Boolean(string="Is Panel Sign", help="Check this to enable the Panel Pricing Calculator on Sales Orders")
