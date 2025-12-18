from odoo import models, fields, api
import math

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # --- PANEL INPUTS ---
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
            # How many signs fit 6x6 on 13x19 press sheet?
            fit1 = int(params.press_w // W) * int(params.press_h // H)
            fit2 = int(params.press_w // H) * int(params.press_h // W)
            signs_per_mold = max(fit1, fit2, 1)
            
            line.panel_signs_per_sheet = signs_per_mold # Display capacity

            # --- 3. PRODUCTION BATCH ---
            # If Q=3 and Capacity=4, we produce 1 Mold (4 signs).
            molds_needed = math.ceil(Q / signs_per_mold)
            
            # Total signs produced (Stock)
            qty_produced = molds_needed * signs_per_mold

            # --- 4. MATERIAL COSTS ---
            # We charge for the FRACTION of the Master Sheets used.
            # Master Sheet holds 17 Molds (default).
            fraction_master_sheet = molds_needed / params.molds_per_sheet 

            # A. Pionite
            cost_pionite = fraction_master_sheet * params.pionite_sheet_cost
            
            # B. Substrate (ABS/Acrylic)
            sub_sheet_cost = 0.0
            if line.panel_material == 'abs':
                if line.panel_thickness == 'three_sixteenth':
                    sub_sheet_cost = params.abs_316_sheet_cost
                else:
                    sub_sheet_cost = params.abs_18_sheet_cost
            else:
                sub_sheet_cost = params.acrylic_18_sheet_cost
            
            cost_substrate = fraction_master_sheet * sub_sheet_cost

            # C. Windows
            cost_window = 0.0
            if line.is_windowed and line.window_height > 0:
                # Window logic uses smaller sheets (24x48).
                # Calculate simple yield: Area of window vs Area of sheet
                # Or use reference fractional logic if parameters exist.
                # Simplification: Assume window sheet yields roughly half a master per sq/inch or similar
                # Using explicit sheet logic from params:
                # signs_per_win_sheet = fit_windows...
                # For robustness, let's treat it as a fraction of the Window Sheet cost based on area usage * safety factor
                cost_window = (molds_needed / params.molds_per_sheet) * params.window_sheet_cost # Rough approximation of 1:1 ratio with master usage scaling

            # D. Consumables (Per Produced Sign)
            # Ink + Paint + Hotstamp are per SIGN produced
            consumables_variable = (
                (params.ink_per_sign * qty_produced) +
                (params.paint_per_sign * qty_produced) +
                (params.hotstamp_per_sign * qty_produced)
            )
            
            # Tape + Lube are per MOLD
            consumables_fixed = (
                (params.tape_per_mold * molds_needed) +
                (params.mclube_per_mold * molds_needed)
            )
            
            total_consumables = consumables_variable + consumables_fixed

            # TOTAL MATERIAL
            total_material = cost_pionite + cost_substrate + cost_window + total_consumables
            line.panel_cost_materials = total_material

            # --- 5. LABOR COSTS ---
            # Labor is per Mold
            total_labor = molds_needed * params.labor_rate_worst
            line.panel_cost_labor = total_labor

            # --- 6. FINAL PRICING ---
            total_batch_cost = total_material + total_labor
            
            # Overhead
            overhead = total_batch_cost * params.overhead_pct
            
            # Gross Price for the Batch
            gross_price_batch = (total_batch_cost + overhead) * params.markup_multiplier
            
            # PRICE PER UNIT
            # Based on CAPACITY (Generated Stock), not Qty ordered
            # If we make 4, and you order 1, the price is (BatchCost / 4).
            # If you order 4, the price is (BatchCost / 4).
            # This ensures price stability.
            
            unit_price = gross_price_batch / qty_produced
            
            line.price_unit = unit_price
