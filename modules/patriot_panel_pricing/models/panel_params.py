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
    # These remain as floats because they define "How much of the product is used"
    molds_per_sheet = fields.Integer(string="Molds per Master Sheet", default=17, help="How many 13x19 press sheets fit in a Master 4x8?")
    
    # Consumable Usage
    ink_per_sign = fields.Float(string="Ink Cost/Alloc per Sign", default=0.05, help="Estimated cost/qty of ink per sign")
    paint_per_sign = fields.Float(string="Paint Cost/Alloc per Sign", default=0.05)
    hotstamp_per_sign = fields.Float(string="Hotstamp Cost/Alloc per Sign", default=0.05)
    
    tape_per_mold = fields.Float(string="Tape Cost/Alloc per Mold", default=0.50)
    mclube_per_mold = fields.Float(string="Lube Cost/Alloc per Mold", default=0.25)
    
    # --- LABOR SPECS ---
    labor_rate_worst = fields.Float(string="Labor Rate ($/hr)", default=100.0, help="Backup rate if Product cost is 0. Used for calculation.")

    # --- MACHINE SPECS ---
    markup_multiplier = fields.Float(string="Markup Multiplier", default=2.4)
    overhead_pct = fields.Float(string="Overhead %", default=0.10)
    
    press_w = fields.Float(string="Press Width", default=13.0)
    press_h = fields.Float(string="Press Height", default=19.0)

    @api.model
    def get_default_params(self):
        # Return the first active param set
        return self.search([('active', '=', True)], limit=1)
