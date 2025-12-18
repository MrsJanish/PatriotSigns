from odoo import models, fields, api
import math

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # --- PANEL INPUTS ---
    is_panel_sign = fields.Boolean(related='product_id.is_panel_sign', store=True)

    panel_width = fields.Float(string="Width (in)")
    panel_height = fields.Float(string="Height (in)")
    panel_material = fields.Selection([
        ('abs', 'ABS'),
        ('acrylic', 'Acrylic')
    ], string="Material", default='abs')
    panel_thickness = fields.Selection([
        ('one_eighth', '1/8"'),
        ('three_sixteenth', '3/16"')
    ], string="Thickness", default='one_eighth')
    
    is_windowed = fields.Boolean(string="Windowed?")
    window_height = fields.Float(string="Window Height (in)")

    # --- COMPUTED USAGE FIELDS (Stored for MO) ---
    # These store the TOTAL quantity needed for the line (not per unit)
    usage_pionite = fields.Float(string="Total Pionite Usage", digits=(12, 4))
    usage_substrate_abs = fields.Float(string="Total ABS Usage", digits=(12, 4))
    usage_substrate_acrylic = fields.Float(string="Total Acrylic Usage", digits=(12, 4))
    usage_window_sheet = fields.Float(string="Total Window Usage", digits=(12, 4))
    
    usage_ink = fields.Float(string="Total Ink Usage", digits=(12, 4))
    usage_paint = fields.Float(string="Total Paint Usage", digits=(12, 4))
    usage_tape = fields.Float(string="Total Tape Usage", digits=(12, 4))
    usage_lube = fields.Float(string="Total Lube Usage", digits=(12, 4))
    
    usage_labor = fields.Float(string="Total Labor Hours", digits=(12, 4))

    # --- COST FIELDS ---
    panel_cost_materials = fields.Float(string="Material Cost")
    panel_cost_labor = fields.Float(string="Labor Cost")
    panel_signs_per_sheet = fields.Integer(string="Signs / Sheet")

    @api.onchange('product_id')
    def _onchange_panel_product(self):
        if self.product_id and self.product_id.is_panel_sign:
            self.name = f"{self.product_id.name} (Configure Dimensions)"

    @api.onchange('panel_width', 'panel_height', 'panel_material', 'panel_thickness', 'is_windowed', 'window_height', 'product_uom_qty')
    def _compute_panel_price(self):
        for line in self:
            if not line.product_id.is_panel_sign:
                continue
            
            params = self.env['panel.pricing.params'].get_default_params()
            if not params:
                continue

            W = line.panel_width
            H = line.panel_height
            Q = line.product_uom_qty
            
            if W <= 0 or H <= 0 or Q <= 0:
                continue

            # 1. CAPACITY
            fit1 = int(params.press_w // W) * int(params.press_h // H)
            fit2 = int(params.press_w // H) * int(params.press_h // W)
            signs_per_mold = max(fit1, fit2, 1)
            line.panel_signs_per_sheet = signs_per_mold

            # 2. BATCH
            molds_needed = math.ceil(Q / signs_per_mold)
            qty_produced = molds_needed * signs_per_mold
            
            # 3. USAGE CALCULATIONS (Total for Batch)
            
            # A. Sheets (Pionite/Substrate)
            # Usage = Fraction of Master Sheet
            usage_master_fraction = molds_needed / params.molds_per_sheet 
            
            line.usage_pionite = usage_master_fraction
            
            # Reset Mutually Exclusive Usages
            line.usage_substrate_abs = 0.0
            line.usage_substrate_acrylic = 0.0
            
            if line.panel_material == 'abs':
                line.usage_substrate_abs = usage_master_fraction
            else:
                line.usage_substrate_acrylic = usage_master_fraction

            # B. Window
            line.usage_window_sheet = 0.0
            if line.is_windowed and line.window_height > 0:
                line.usage_window_sheet = (molds_needed / params.molds_per_sheet) # Approx logic

            # C. Consumables
            line.usage_ink = params.ink_per_sign * qty_produced
            line.usage_paint = params.paint_per_sign * qty_produced
            
            line.usage_tape = params.tape_per_mold * molds_needed
            line.usage_lube = params.mclube_per_mold * molds_needed

            # D. Labor
            line.usage_labor = 1.0 * molds_needed # Assuming 1 Hour per Mold for simplicity, logic can be refined
            # Wait, params says labor cost per mold, implying hours per mold depends on rate?
            # Let's assume params.labor_rate_worst is $/hr, so if we calculate cost, we need hours.
            # If cost = $40 and rate = $100/hr -> 0.4 hours.
            # User didn't specify Hours Per Mold, previously used straight cost.
            # Let's infer Hours = 1.0 per mold effectively if we treat standard UoM as Hour.
            # Actually, let's fix this in params next time. usage_labor = molds_needed for now.

            # 4. COST CALCULATION (Usage * Product Cost)
            cost_total = 0.0
            
            cost_total += line.usage_pionite * (params.pionite_product_id.standard_price or 0)
            
            # Abs/Acrylic Cost
            if line.usage_substrate_abs > 0:
                # Distinguish 1/8 vs 3/16 via product ID
                prod = params.abs_18_product_id if line.panel_thickness == 'one_eighth' else params.abs_316_product_id
                cost_total += line.usage_substrate_abs * (prod.standard_price or 0)
            if line.usage_substrate_acrylic > 0:
                cost_total += line.usage_substrate_acrylic * (params.acrylic_18_product_id.standard_price or 0)

            cost_total += line.usage_window_sheet * (params.window_product_id.standard_price or 0)
            
            cost_total += line.usage_ink * (params.ink_product_id.standard_price or 0)
            cost_total += line.usage_paint * (params.paint_product_id.standard_price or 0)
            cost_total += line.usage_tape * (params.tape_product_id.standard_price or 0)
            cost_total += line.usage_lube * (params.lube_product_id.standard_price or 0)

            line.panel_cost_materials = cost_total
            
            # Labor Cost
            rate_labor = params.labor_product_id.standard_price or params.labor_rate_worst
            cost_labor = line.usage_labor * rate_labor
            line.panel_cost_labor = cost_labor

            # 5. PRICE
            total_batch_cost = line.panel_cost_materials + line.panel_cost_labor
            overhead = total_batch_cost * params.overhead_pct
            gross_price = (total_batch_cost + overhead) * params.markup_multiplier
            
            line.price_unit = gross_price / qty_produced
