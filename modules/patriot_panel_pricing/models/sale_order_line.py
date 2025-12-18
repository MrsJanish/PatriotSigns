from odoo import models, fields, api
import math

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # --- PANEL INPUTS ---
    # We add related field to helper UI visibility logic
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

    # --- COMPUTED COST FIELDS ---
    panel_cost_materials = fields.Float(string="Material Cost")
    panel_cost_labor = fields.Float(string="Labor Cost")
    panel_waste_pct = fields.Float(string="Waste %")
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
            
            # 1. Get Configuration
            params = self.env['panel.pricing.params'].get_default_params()
            if not params:
                continue

            W = line.panel_width
            H = line.panel_height
            Q = line.product_uom_qty
            
            if W <= 0 or H <= 0 or Q <= 0:
                continue

            # --- 2. CAPACITY (SIGNS PER MOLD) ---
            fit1 = int(params.press_w // W) * int(params.press_h // H)
            fit2 = int(params.press_w // H) * int(params.press_h // W)
            signs_per_mold = max(fit1, fit2, 1)
            line.panel_signs_per_sheet = signs_per_mold

            # --- 3. PRODUCTION BATCH ---
            molds_needed = math.ceil(Q / signs_per_mold)
            qty_produced = molds_needed * signs_per_mold

            # --- 4. MATERIAL COSTS ---
            # Fetch Costs from DEFINED PRODUCTS in Params
            # Use 'standard_price' (Cost) from the product record
            
            cost_master_pionite = params.pionite_product_id.standard_price or 0.0
            
            cost_abs_18 = params.abs_18_product_id.standard_price or 0.0
            cost_abs_316 = params.abs_316_product_id.standard_price or 0.0
            cost_acrylic = params.acrylic_18_product_id.standard_price or 0.0
            cost_window_sheet = params.window_product_id.standard_price or 0.0

            # Fraction Used
            fraction_master = molds_needed / params.molds_per_sheet 

            # A. Pionite
            cost_pionite = fraction_master * cost_master_pionite
            
            # B. Substrate
            sub_sheet_cost = 0.0
            if line.panel_material == 'abs':
                if line.panel_thickness == 'three_sixteenth':
                    sub_sheet_cost = cost_abs_316
                else:
                    sub_sheet_cost = cost_abs_18
            else:
                sub_sheet_cost = cost_acrylic
            
            cost_substrate = fraction_master * sub_sheet_cost

            # C. Windows
            cost_window = 0.0
            if line.is_windowed and line.window_height > 0:
                cost_window = (molds_needed / params.molds_per_sheet) * cost_window_sheet

            # D. Consumables
            # Note: Ideally these costs also come from products (ink, etc.)
            # For now, we use the float usage rate * product cost if available, or just the float cost.
            # Let's stick to the simple defined floats for "Cost per Sign" for consumables as they are small variance.
            
            consumables_variable = (
                (params.ink_per_sign * qty_produced) +
                (params.paint_per_sign * qty_produced) +
                (params.hotstamp_per_sign * qty_produced)
            )
            
            consumables_fixed = (
                (params.tape_per_mold * molds_needed) +
                (params.mclube_per_mold * molds_needed)
            )
            
            total_consumables = consumables_variable + consumables_fixed

            # TOTAL MATERIAL
            total_material = cost_pionite + cost_substrate + cost_window + total_consumables
            line.panel_cost_materials = total_material

            # --- 5. LABOR COSTS ---
            # Use Labor Product Cost if available, else fallback
            rate_labor = params.labor_product_id.standard_price if params.labor_product_id else params.labor_rate_worst
            if rate_labor <= 0: rate_labor = params.labor_rate_worst

            total_labor = molds_needed * rate_labor
            line.panel_cost_labor = total_labor

            # --- 6. FINAL PRICING ---
            total_batch_cost = total_material + total_labor
            
            overhead = total_batch_cost * params.overhead_pct
            gross_price_batch = (total_batch_cost + overhead) * params.markup_multiplier
            
            unit_price = gross_price_batch / qty_produced
            
            line.price_unit = unit_price
