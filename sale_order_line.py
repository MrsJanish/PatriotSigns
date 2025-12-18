# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # Mark which products should use the panel pricing engine
    panel_is_panel_sign = fields.Boolean(string="Is Panel Sign")


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # Dummy trigger field; value not important, compute does all the work
    panel_pricing_trigger = fields.Float(
        string="Panel Pricing Trigger",
        compute="_compute_panel_pricing",
        store=False,
    )

    @api.depends(
        "product_id",
        "product_uom_qty",
        "x_studio_sign_width_in",
        "x_studio_sign_height_in",
        "x_studio_windowed",
        "x_studio_window_height_in",
        "x_studio_variant",
        "x_studio_thickness",
    )
    def _compute_panel_pricing(self):
        """
        Central pricing engine for panel signs.
        Writes into:
          - price_unit
          - x_studio_* cost / waste fields (already created via Studio)

        Assumptions for selection keys:
          x_studio_variant   -> 'abs' or 'acrylic'
          x_studio_thickness -> 'one_eighth' or 'three_sixteenth'
        """
        for line in self:
            # Default: do nothing if not a panel sign product
            tmpl = line.product_id.product_tmpl_id if line.product_id else False
            if not tmpl or not tmpl.panel_is_panel_sign:
                continue

            W = line.x_studio_sign_width_in or 0.0
            H = line.x_studio_sign_height_in or 0.0
            Q = line.product_uom_qty or 0.0

            if W <= 0.0 or H <= 0.0 or Q <= 0.0:
                continue

            windowed = bool(line.x_studio_windowed)
            Wh = line.x_studio_window_height_in or 0.0
            if not windowed:
                Wh = 0.0

            variant = line.x_studio_variant or "abs"
            thickness = line.x_studio_thickness or "one_eighth"

            # Sheet geometry
            PIONITE_W, PIONITE_H = 49.0, 97.0
            SUB_W, SUB_H = 48.0, 96.0
            WIN_W, WIN_H = 24.0, 48.0

            PIONITE_AREA = PIONITE_W * PIONITE_H
            SUB_AREA = SUB_W * SUB_H
            WIN_AREA = WIN_W * WIN_H

            # Costs per sheet
            PIONITE_SHEET_COST = 211.30  # using <30 tier as baseline
            ABS_18_SHEET_COST = 80.0
            ABS_316_SHEET_COST = 130.0
            ACRYLIC_18_SHEET_COST = 110.0
            WINDOW_SHEET_COST = 75.0

            # Press sheet info
            PRESS_W, PRESS_H = 13.0, 19.0
            MOLDS_PER_SHEET = 17

            # Consumables
            INK_PER_SIGN = 0.33
            TAPE_PER_MOLD = 0.25
            MCLUBE_PER_MOLD = 0.50
            PAINT_PER_SIGN = 0.60
            HOTSTAMP_PER_SIGN = 0.02

            # Labor per mold
            LABOR_PER_MOLD_BEST = 40.0
            LABOR_PER_MOLD_WORST = 100.0

            # Overhead & markup
            OVERHEAD_PCT = 0.15   # 15% overhead
            MARKUP_MULT = 2.40    # final multiplier on (cost + overhead)

            # --- GEOMETRY ---
            sign_area = W * H
            if sign_area <= 0:
                continue

            window_area_sign = W * Wh if (windowed and Wh > 0) else 0.0
            pionite_area_per_sign = max(sign_area - window_area_sign, 0.0)
            substrate_area_per_sign = sign_area
            window_area_per_sign = window_area_sign

            # --- SIGNS PER MOLD ---
            fit1 = int(PRESS_W // W) * int(PRESS_H // H)
            fit2 = int(PRESS_W // H) * int(PRESS_H // W)
            signs_per_mold = max(fit1, fit2, 1)
            line.x_studio_signs_per_mold = float(signs_per_mold)

            # Molds needed (ceil)
            molds_needed = int((Q + signs_per_mold - 1.0) // signs_per_mold)
            if molds_needed < 1:
                molds_needed = 1
            line.x_studio_molds_needed = float(molds_needed)

            # --- SHEETS NEEDED ---
            signs_per_sheet = signs_per_mold * MOLDS_PER_SHEET
            if signs_per_sheet < 1:
                signs_per_sheet = 1

            sheets_needed_pionite = int((Q + signs_per_sheet - 1.0) // signs_per_sheet)
            sheets_needed_sub = int((Q + signs_per_sheet - 1.0) // signs_per_sheet)

            # Window sheets
            if window_area_per_sign > 0.0 and Wh > 0.0:
                fit1w = int(WIN_W // W) * int(WIN_H // Wh)
                fit2w = int(WIN_W // Wh) * int(WIN_H // W)
                win_per_sheet = max(fit1w, fit2w, 1)
                sheets_needed_win = int((Q + win_per_sheet - 1.0) // win_per_sheet)
            else:
                win_per_sheet = 0
                sheets_needed_win = 0

            # --- WASTE ---
            # Pionite
            used_pionite = Q * pionite_area_per_sign
            total_pionite_area = sheets_needed_pionite * PIONITE_AREA
            waste_pionite = 0.0
            if total_pionite_area > 0:
                waste_pionite = 1.0 - (used_pionite / total_pionite_area)
            waste_pionite = max(0.0, min(waste_pionite, 1.0))

            line.x_studio_pionite_usage_total_in = used_pionite
            line.x_studio_pionite_waste_ = waste_pionite * 100.0

            # Substrate
            used_sub = Q * substrate_area_per_sign
            total_sub_area = sheets_needed_sub * SUB_AREA
            waste_sub = 0.0
            if total_sub_area > 0:
                waste_sub = 1.0 - (used_sub / total_sub_area)
            waste_sub = max(0.0, min(waste_sub, 1.0))

            line.x_studio_substrate_usage_total_in = used_sub
            line.x_studio_substrate_waste_ = waste_sub * 100.0

            # Window
            if window_area_per_sign > 0.0 and sheets_needed_win > 0:
                used_win = Q * window_area_per_sign
                total_win_area = sheets_needed_win * WIN_AREA
                waste_win = 0.0
                if total_win_area > 0:
                    waste_win = 1.0 - (used_win / total_win_area)
                waste_win = max(0.0, min(waste_win, 1.0))
            else:
                used_win = 0.0
                waste_win = 0.0

            line.x_studio_window_usage_total_in = used_win
            line.x_studio_window_waste_ = waste_win * 100.0

            # --- MATERIAL COSTS ---
            pionite_cost = sheets_needed_pionite * PIONITE_SHEET_COST

            if variant == "abs":
                if thickness == "three_sixteenth":
                    substrate_sheet_cost = ABS_316_SHEET_COST
                else:
                    substrate_sheet_cost = ABS_18_SHEET_COST
            else:
                substrate_sheet_cost = ACRYLIC_18_SHEET_COST

            substrate_cost = sheets_needed_sub * substrate_sheet_cost
            window_cost = sheets_needed_win * WINDOW_SHEET_COST if sheets_needed_win > 0 else 0.0

            ink_cost = INK_PER_SIGN * Q
            paint_cost = PAINT_PER_SIGN * Q
            hotstamp_cost = HOTSTAMP_PER_SIGN * Q
            tape_cost = TAPE_PER_MOLD * molds_needed
            mclube_cost = MCLUBE_PER_MOLD * molds_needed

            materials_total = (
                pionite_cost
                + substrate_cost
                + window_cost
                + ink_cost
                + paint_cost
                + hotstamp_cost
                + tape_cost
                + mclube_cost
            )
            line.x_studio_material_cost_total = materials_total

            # --- LABOR ---
            labor_best = LABOR_PER_MOLD_BEST * molds_needed
            labor_worst = LABOR_PER_MOLD_WORST * molds_needed
            line.x_studio_labor_cost_best = labor_best
            line.x_studio_labor_cost_worst = labor_worst

            total_best = materials_total + labor_best
            total_worst = materials_total + labor_worst
            line.x_studio_total_cost_best = total_best
            line.x_studio_total_cost_worst = total_worst

            if Q > 0:
                cps_best = total_best / Q
                cps_worst = total_worst / Q
            else:
                cps_best = 0.0
                cps_worst = 0.0

            line.x_studio_cost_per_sign_best = cps_best
            line.x_studio_cost_per_sign_worst = cps_worst

            # --- OVERHEAD & PRICING ---
            overhead_worst = total_worst * OVERHEAD_PCT
            line.x_studio_overhead_ = OVERHEAD_PCT * 100.0  # stored as %

            cost_with_overhead_worst = total_worst + overhead_worst
            sell_price_per_sign = cost_with_overhead_worst * MARKUP_MULT if Q > 0 else 0.0

            line.x_studio_markup_multiplier = MARKUP_MULT
            line.x_studio_final_sell_price = sell_price_per_sign

            # Profit margin % vs cost+overhead (worst-case)
            if sell_price_per_sign > 0.0:
                unit_cost_with_overhead = cost_with_overhead_worst / Q
                profit_margin_pct_worst = (
                    (sell_price_per_sign - unit_cost_with_overhead) / sell_price_per_sign
                ) * 100.0
            else:
                profit_margin_pct_worst = 0.0
            line.x_studio_profit_margin_worst = profit_margin_pct_worst

            # Sync with Odoo's unit price
            line.price_unit = sell_price_per_sign

            # Store final price on the trigger field too (for convenience)
            line.panel_pricing_trigger = sell_price_per_sign
