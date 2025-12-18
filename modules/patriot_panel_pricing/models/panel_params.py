from odoo import models, fields, api

class PanelPricingParams(models.Model):
    _name = "panel.pricing.params"
    _description = "Panel Pricing Configuration"

    name = fields.Char(string="Configuration Name", default="Default Configuration", required=True)
    active = fields.Boolean(default=True)

    # --- MATERIALS (LINKED TO PRODUCTS) ---
    pionite_product_id = fields.Many2one('product.product', string="Pionite Sheet Product", required=True)
    abs_18_product_id = fields.Many2one('product.product', string="ABS 1/8 Product", required=True)
    abs_316_product_id = fields.Many2one('product.product', string="ABS 3/16 Product", required=True)
    acrylic_18_product_id = fields.Many2one('product.product', string="Acrylic 1/8 Product", required=True)
    window_product_id = fields.Many2one('product.product', string="Window/Lens Product", required=True)

    # --- CONSUMABLES (LINKED TO PRODUCTS) ---
    ink_product_id = fields.Many2one('product.product', string="Ink Product")
    paint_product_id = fields.Many2one('product.product', string="Paint Product")
    tape_product_id = fields.Many2one('product.product', string="Tape Product")
    lube_product_id = fields.Many2one('product.product', string="Lube Product")
    
    # --- LABOR (LINKED TO SERVICE) ---
    labor_product_id = fields.Many2one('product.product', string="Labor Service Product", domain="[('type','=','service')]")

    # --- QUANTITIES (Usage Rates) ---
    molds_per_sheet = fields.Integer(string="Molds per Master Sheet", default=17, help="How many 13x19 press sheets fit in a Master 4x8?")
    
    # Consumable Usage (UNITS PER SIGN / MOLD)
    # Changed label to emphasize Quantity
    ink_per_sign = fields.Float(string="Ink Units per Sign", default=0.05, help="Qty of Ink Product used per sign")
    paint_per_sign = fields.Float(string="Paint Units per Sign", default=0.05)
    hotstamp_per_sign = fields.Float(string="Hotstamp Units per Sign", default=0.05)
    
    tape_per_mold = fields.Float(string="Tape Units per Mold", default=0.50)
    mclube_per_mold = fields.Float(string="Lube Units per Mold", default=0.25)
    
    # --- LABOR SPECS ---
    # Kept for fallback, but product cost preferred
    labor_rate_worst = fields.Float(string="Fallback Labor Rate ($/hr)", default=100.0)

    # --- MACHINE SPECS ---
    markup_multiplier = fields.Float(string="Markup Multiplier", default=2.4)
    overhead_pct = fields.Float(string="Overhead %", default=0.10)
    
    press_w = fields.Float(string="Press Width", default=13.0)
    press_h = fields.Float(string="Press Height", default=19.0)

    @api.model
    def get_default_params(self):
        return self.search([('active', '=', True)], limit=1)
