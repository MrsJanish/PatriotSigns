from odoo import models, api

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.model_create_multi
    def create(self, vals_list):
        productions = super(MrpProduction, self).create(vals_list)
        
        for mo in productions:
            # Check if originating from Sale Order
            # We look for the 'procurement_group_id' which links back to the Sale Order
            if not mo.procurement_group_id:
                continue
            
            # Find the Sale Order Lines related to this procurement group
            # Note: This finds ALL lines in the SO, we need the specific one triggering this MO.
            # A stock move usually links the MO to the SOL via created_production_ids or similar (depending on route).
            # Reliable method: Check move_dest_ids of the finished product move?
            
            # Simplified approach: Look for a stock.move that created this MO and has a sale_line_id
            # Odoo 16+ links: sale_line_id -> procurement_group -> stock.move (production) -> MO
            
            # Let's try to find the sale line via the move_dest_ids of the finished product if MTO
            # Or assume 1:1 if the procurement group matches
            
            # We need to find the specific line that triggered this product.
            sale_lines = self.env['sale.order.line'].search([
                ('order_id.procurement_group_id', '=', mo.procurement_group_id.id),
                ('product_id', '=', mo.product_id.id)
            ])
            
            if not sale_lines:
                continue
                
            # Use the first one found (assuming splitting logic handles others or 1 line per product variant)
            line = sale_lines[0]
            
            if not line.is_panel_sign:
                continue

            # GET PARAMS
            params = self.env['panel.pricing.params'].get_default_params()
            if not params:
                continue

            # DEFINE COMPONENT MAPPING
            # Product ID -> Usage Field on Line
            # We map the Configured Product (in params) to the Field on the Line
            
            component_map = {
                params.pionite_product_id.id: line.usage_pionite,
                params.ink_product_id.id: line.usage_ink,
                params.paint_product_id.id: line.usage_paint,
                params.tape_product_id.id: line.usage_tape,
                params.lube_product_id.id: line.usage_lube,
                params.window_product_id.id: line.usage_window_sheet,
                params.labor_product_id.id: line.usage_labor,
                # Substrate Logic:
                params.abs_18_product_id.id: line.usage_substrate_abs if line.panel_thickness == 'one_eighth' else 0,
                params.abs_316_product_id.id: line.usage_substrate_abs if line.panel_thickness == 'three_sixteenth' else 0,
                params.acrylic_18_product_id.id: line.usage_substrate_acrylic
            }

            # UPDATE MOVES
            # Iterate over the raw material moves (components)
            for move in mo.move_raw_ids:
                prod_id = move.product_id.id
                if prod_id in component_map:
                    new_qty = component_map[prod_id]
                    if new_qty > 0:
                        move.product_uom_qty = new_qty
                    else:
                        # If usage is 0 (e.g. acrylic when using abs), set to 0?
                        # Or maybe user didn't put it in BoM if not needed?
                        # If it IS in BoM but usage is 0, we can set to 0.
                        move.product_uom_qty = 0

            # HANDLE MISSING MOVES?
            # If the base BoM didn't have the component (e.g. Window), we might need to create it.
            # For now, we assume the user puts ALL potential items in the Master BoM with 0 qty.
            
        return productions
