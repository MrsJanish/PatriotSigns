# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    # Pricing Parameters
    pricing_overhead_pct = fields.Float(string='Overhead %', default=15.0)
    pricing_markup_mult = fields.Float(string='Markup Multiplier', default=2.4)
    
    # Labor Rates
    shop_labor_rate = fields.Float(string='Shop Labor Rate ($/hr)', default=75.0)
    install_labor_rate = fields.Float(string='Install Labor Rate ($/hr)', default=100.0)
    
    # Material Costs (Defaults for calculation if product not linked)
    cost_pionite_sheet = fields.Float(string='Pionite Sheet Cost', default=211.30)
    cost_abs_18_sheet = fields.Float(string='ABS 1/8 Sheet Cost', default=80.00)
    cost_abs_316_sheet = fields.Float(string='ABS 3/16 Sheet Cost', default=130.00)
    cost_acrylic_sheet = fields.Float(string='Acrylic Sheet Cost', default=110.00)
    cost_window_sheet = fields.Float(string='Window Sheet Cost', default=75.00)
    
    # Consumables
    cost_ink_per_unit = fields.Float(string='Ink Cost (per sign)', default=0.33)
    cost_paint_per_unit = fields.Float(string='Paint Cost (per sign)', default=0.60)
    cost_tape_per_mold = fields.Float(string='Tape Cost (per mold)', default=0.25)
    cost_mclube_per_mold = fields.Float(string='McLube Cost (per mold)', default=0.50)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pricing_overhead_pct = fields.Float(related='company_id.pricing_overhead_pct', readonly=False)
    pricing_markup_mult = fields.Float(related='company_id.pricing_markup_mult', readonly=False)
    shop_labor_rate = fields.Float(related='company_id.shop_labor_rate', readonly=False)
    install_labor_rate = fields.Float(related='company_id.install_labor_rate', readonly=False)
    
    cost_pionite_sheet = fields.Float(related='company_id.cost_pionite_sheet', readonly=False)
    cost_abs_18_sheet = fields.Float(related='company_id.cost_abs_18_sheet', readonly=False)
    cost_abs_316_sheet = fields.Float(related='company_id.cost_abs_316_sheet', readonly=False)
    cost_acrylic_sheet = fields.Float(related='company_id.cost_acrylic_sheet', readonly=False)
    cost_window_sheet = fields.Float(related='company_id.cost_window_sheet', readonly=False)
    
    cost_ink_per_unit = fields.Float(related='company_id.cost_ink_per_unit', readonly=False)
    cost_paint_per_unit = fields.Float(related='company_id.cost_paint_per_unit', readonly=False)
    cost_tape_per_mold = fields.Float(related='company_id.cost_tape_per_mold', readonly=False)
    cost_mclube_per_mold = fields.Float(related='company_id.cost_mclube_per_mold', readonly=False)
