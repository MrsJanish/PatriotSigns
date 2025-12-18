from odoo import models, fields, api

class PanelPricingParams(models.Model):
    _name = 'panel.pricing.params'
    _description = 'Panel Pricing Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Configuration Name', default='Default Configuration', required=True)
    active = fields.Boolean(default=True)

    # --- SHEET COSTS ---
    pionite_sheet_cost = fields.Float(string="Pionite Cost ($/sheet)", default=211.30, help="Cost of a 49x97 Pionite sheet")
    abs_18_sheet_cost = fields.Float(string="ABS 1/8 Cost ($/sheet)", default=80.00)
    abs_316_sheet_cost = fields.Float(string="ABS 3/16 Cost ($/sheet)", default=130.00)
    acrylic_18_sheet_cost = fields.Float(string="Acrylic 1/8 Cost ($/sheet)", default=110.00)
    window_sheet_cost = fields.Float(string="Window Sheet Cost ($/sheet)", default=75.00)

    # --- GEOMETRY ---
    pionite_w = fields.Float(default=49.0)
    pionite_h = fields.Float(default=97.0)
    sub_w = fields.Float(default=48.0)
    sub_h = fields.Float(default=96.0)
    win_w = fields.Float(default=24.0)
    win_h = fields.Float(default=48.0)
    
    press_w = fields.Float(string="Press Width", default=13.0)
    press_h = fields.Float(string="Press Height", default=19.0)
    molds_per_sheet = fields.Integer(string="Molds per Press Sheet", default=17)

    # --- CONSUMABLES ---
    ink_per_sign = fields.Float(string="Ink Cost per Sign", default=0.33)
    paint_per_sign = fields.Float(string="Paint Cost per Sign", default=0.60)
    tape_per_mold = fields.Float(string="Tape Cost per Mold", default=0.25)
    mclube_per_mold = fields.Float(string="McLube per Mold", default=0.50)
    hotstamp_per_sign = fields.Float(string="Hotstamp Cost per Sign", default=0.02)

    # --- LABOR ---
    labor_rate_best = fields.Float(string="Labor Cost per Mold (Best Case)", default=40.00)
    labor_rate_worst = fields.Float(string="Labor Cost per Mold (Worst Case)", default=100.00)

    # --- MARKUP ---
    overhead_pct = fields.Float(string="Overhead Multiplier", default=0.15, help="e.g. 0.15 for 15%")
    markup_multiplier = fields.Float(string="Final Price Multiplier", default=2.40)

    @api.model
    def get_default_params(self):
        """Helper to get the active configuration"""
        return self.search([('active', '=', True)], limit=1)
