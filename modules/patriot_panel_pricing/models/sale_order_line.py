from odoo import models, fields, api

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

    # --- COMPUTED COST FIELDS (Visible for analysis) ---
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

            # 2. Extract specific values from params (caching/optimizing helps, but simple read fine for now)
            # Geometry
            W, H = line.panel_width, line.panel_height
            if W <= 0 or H <= 0 or line.product_uom_qty <= 0:
                continue

            # --- LOGIC PORTED FROM REFERENCE ---
            # Press fit logic
            fit1 = int(params.press_w // W) * int(params.press_h // H)
            fit2 = int(params.press_w // H) * int(params.press_h // W)
            signs_per_mold = max(fit1, fit2, 1)
            
            molds_needed = -(-line.product_uom_qty // signs_per_mold) # Ceiling div
            
            signs_per_sheet = signs_per_mold * params.molds_per_sheet
            line.panel_signs_per_sheet = signs_per_sheet
            
            sheets_needed = -(-line.product_uom_qty // signs_per_sheet) # Ceiling div

            # Material Cost Selection
            sub_sheet_cost = 0.0
            if line.panel_material == 'abs':
                if line.panel_thickness == 'three_sixteenth':
                    sub_sheet_cost = params.abs_316_sheet_cost
                else:
                    sub_sheet_cost = params.abs_18_sheet_cost
            else:
                sub_sheet_cost = params.acrylic_18_sheet_cost

            # Calculate Totals
            pionite_total = sheets_needed * params.pionite_sheet_cost
            sub_total = sheets_needed * sub_sheet_cost
            
            # Window Logic
            window_total = 0.0
            if line.is_windowed and line.window_height > 0:
                 # Simplified window logic for robustness
                 window_total = sheets_needed * params.window_sheet_cost

            # Consumables
            consumables = (
                (params.ink_per_sign * line.product_uom_qty) +
                (params.paint_per_sign * line.product_uom_qty) +
                (params.hotstamp_per_sign * line.product_uom_qty) +
                (params.tape_per_mold * molds_needed) +
                (params.mclube_per_mold * molds_needed)
            )

            material_cost = pionite_total + sub_total + window_total + consumables
            
            # Labor (Using Worst Case for safety as default)
            labor_cost = params.labor_rate_worst * molds_needed

            total_cost = material_cost + labor_cost
            
            # Overhead
            overhead = total_cost * params.overhead_pct
            
            # Final Price
            final_price = (total_cost + overhead) * params.markup_multiplier
            
            unit_price = final_price / line.product_uom_qty if line.product_uom_qty else 0.0

            # Write values
            line.price_unit = unit_price
            line.panel_cost_materials = material_cost
            line.panel_cost_labor = labor_cost
            
            # Waste Calculation (Simple Area)
            sheet_area = params.pionite_w * params.pionite_h
            used_area = W * H * line.product_uom_qty
            total_area = sheets_needed * sheet_area
            if total_area > 0:
                line.panel_waste_pct = (1.0 - (used_area / total_area)) * 100
