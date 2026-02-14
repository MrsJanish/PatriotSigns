# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Estimate(models.Model):
    """
    Estimate - Cost estimate for a sign project.
    
    Created from CRM opportunity, contains detailed line items
    for each sign type with material, labor, and installation costs.
    """
    _name = 'ps.estimate'
    _description = 'Sign Estimate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # =========================================================================
    # IDENTIFICATION
    # =========================================================================
    name = fields.Char(
        string='Estimate Number',
        required=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('ps.estimate') or 'New',
        tracking=True
    )
    opportunity_id = fields.Many2one(
        'crm.lead',
        string='Opportunity',
        required=True,
        ondelete='cascade'
    )
    project_name = fields.Char(
        related='opportunity_id.name',
        string='Project Name'
    )
    
    # =========================================================================
    # DATES
    # =========================================================================
    date = fields.Date(
        string='Estimate Date',
        default=fields.Date.today,
        required=True
    )
    valid_until = fields.Date(
        string='Valid Until'
    )
    
    # =========================================================================
    # PARTIES
    # =========================================================================
    gc_partner_id = fields.Many2one(
        related='opportunity_id.gc_partner_id',
        string='General Contractor',
        store=True
    )
    
    # =========================================================================
    # LINES
    # =========================================================================
    line_ids = fields.One2many(
        'ps.estimate.line',
        'estimate_id',
        string='Estimate Lines'
    )
    
    # =========================================================================
    # SHOP LABOR (Mold-based)
    # =========================================================================
    total_molds = fields.Integer(
        string='Total Molds',
        compute='_compute_shop_labor',
        store=True,
        help='Sum of molds needed across all sign types'
    )
    mold_time_minutes = fields.Float(
        string='Time per Mold (min)',
        default=50.0,
        help='Average time to make one mold (default 50 min)'
    )
    shop_rate = fields.Float(
        string='Shop Rate ($/hr)',
        default=85.0,
        help='Hourly rate for shop labor (overhead-loaded)'
    )
    shop_labor_total = fields.Float(
        string='Shop Labor',
        compute='_compute_shop_labor',
        store=True,
        help='Total Molds × Time per Mold × Shop Rate'
    )
    
    # =========================================================================
    # TRAVEL
    # =========================================================================
    travel_miles = fields.Float(
        string='Travel Miles (one-way)',
        help='Distance from shop to job site'
    )
    travel_rate = fields.Float(
        string='Mileage Rate ($/mi)',
        default=0.72,
        help='IRS standard mileage rate (2025: $0.72/mi)'
    )
    travel_trips = fields.Integer(
        string='Number of Trips',
        default=2,
        help='Number of round trips (2 = install + pickup/punchlist)'
    )
    travel_total = fields.Float(
        string='Travel Total',
        compute='_compute_travel',
        store=True,
        help='Miles × Rate × 2 (round trip) × Number of Trips'
    )
    
    # =========================================================================
    # INSTALLATION
    # =========================================================================
    install_hours = fields.Float(
        string='Install Hours',
        default=8.0,
        help='Estimated hours to install all signs'
    )
    install_rate = fields.Float(
        string='Install Rate ($/hr)',
        default=40.0,
        help='Combined crew rate: Robert ($25) + Bryson ($15) = $40/hr'
    )
    install_crew_size = fields.Integer(
        string='Crew Size',
        default=2,
        help='Number of installers (rate already includes 2-person crew at $40/hr)'
    )
    install_total = fields.Float(
        string='Installation Total',
        compute='_compute_install',
        store=True,
        help='Hours × Rate (rate is combined for full crew)'
    )
    
    # =========================================================================
    # EQUIPMENT RENTAL
    # =========================================================================
    needs_equipment = fields.Boolean(
        string='Equipment Needed',
        default=False,
        help='Check if lift, scissor lift, or other equipment rental is needed'
    )
    equipment_type = fields.Selection([
        ('lift', 'Boom Lift'),
        ('scissor', 'Scissor Lift'),
        ('scaffold', 'Scaffolding'),
        ('bucket', 'Bucket Truck'),
        ('other', 'Other'),
    ], string='Equipment Type')
    equipment_days = fields.Float(
        string='Rental Days',
        default=1.0
    )
    equipment_daily_rate = fields.Float(
        string='Daily Rate',
        default=350.0,
        help='Daily rental rate for equipment'
    )
    equipment_delivery = fields.Float(
        string='Delivery/Pickup',
        default=150.0,
        help='Delivery and pickup charges'
    )
    equipment_total = fields.Float(
        string='Equipment Total',
        compute='_compute_equipment',
        store=True,
        help='(Days × Daily Rate) + Delivery'
    )
    
    # =========================================================================
    # TOTALS (Customer-Facing Prices)
    # =========================================================================
    signage_total = fields.Float(
        string='Signage Total',
        compute='_compute_totals',
        store=True,
        help='Sum of all sign prices (unit_price × qty)'
    )
    # NOTE: labor_total removed - not used in customer-facing estimates
    # Shop Labor, Install, and Travel are already at customer rates
    
    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_totals',
        store=True
    )
    
    # NOTE: Markup section removed - markup is already applied to sign prices
    # The estimate total IS the subtotal (no additional markup needed)
    
    # =========================================================================
    # FINAL
    # =========================================================================
    total = fields.Float(
        string='Estimate Total',
        compute='_compute_totals',
        store=True,
        tracking=True,
        help='Final bid price (Signage + Shop + Install + Travel + Equipment)'
    )
    
    # =========================================================================
    # PROFITABILITY
    # =========================================================================
    profit_amount = fields.Float(
        string='Profit $',
        compute='_compute_totals',
        store=True,
        help='Total (bid) - Subtotal (cost) = Profit'
    )
    profit_margin_pct = fields.Float(
        string='Profit Margin %',
        compute='_compute_totals',
        store=True,
        help='Profit as percentage of bid price'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    state = fields.Selection([
        ('draft', 'Draft'),
        ('review', 'Under Review'),
        ('approved', 'Approved'),
        ('submitted', 'Submitted'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    ], string='Status', default='draft', tracking=True)
    
    # =========================================================================
    # NOTES
    # =========================================================================
    notes = fields.Text(
        string='Internal Notes'
    )
    terms = fields.Text(
        string='Terms & Conditions'
    )
    exclusions = fields.Text(
        string='Exclusions'
    )

    # =========================================================================
    # COMPUTED
    # =========================================================================

    @api.depends('line_ids.molds_needed', 'mold_time_minutes', 'shop_rate')
    def _compute_shop_labor(self):
        """Calculate shop labor from mold count"""
        for estimate in self:
            estimate.total_molds = sum(estimate.line_ids.mapped('molds_needed'))
            hours = (estimate.total_molds * estimate.mold_time_minutes) / 60.0
            estimate.shop_labor_total = hours * estimate.shop_rate

    @api.depends('travel_miles', 'travel_rate', 'travel_trips')
    def _compute_travel(self):
        """Calculate travel cost: miles × rate × 2 (round trip) × trips"""
        for estimate in self:
            estimate.travel_total = estimate.travel_miles * estimate.travel_rate * 2 * estimate.travel_trips

    @api.depends('install_hours', 'install_rate')
    def _compute_install(self):
        """Calculate installation cost: hours × rate (rate is combined crew rate)"""
        for estimate in self:
            estimate.install_total = estimate.install_hours * estimate.install_rate

    @api.depends('needs_equipment', 'equipment_days', 'equipment_daily_rate', 'equipment_delivery')
    def _compute_equipment(self):
        """Calculate equipment rental cost: (days × rate) + delivery"""
        for estimate in self:
            if estimate.needs_equipment:
                estimate.equipment_total = (
                    (estimate.equipment_days * estimate.equipment_daily_rate) + 
                    estimate.equipment_delivery
                )
            else:
                estimate.equipment_total = 0.0

    @api.depends('line_ids.line_total',
                 'shop_labor_total', 'travel_total', 'install_total', 
                 'equipment_total')
    def _compute_totals(self):
        """
        Calculate CUSTOMER-FACING totals (PRICES, not costs).
        
        Structure:
        - Signage Total: Sum of line_total (unit_price × qty) for each sign type
        - Shop Fee: Charged at shop_rate (customer rate)
        - Install Fee: Charged at install_rate (customer rate)
        - Travel Fee: Miles × rate
        - Equipment Fee: Rental charges (pass-through)
        
        NO ADDITIONAL MARKUP - prices already include markup on signs.
        """
        for estimate in self:
            # =================================================================
            # CUSTOMER-FACING PRICES
            # =================================================================
            
            # Signage Total = sum of (unit_price × quantity) for all lines
            signage = sum(estimate.line_ids.mapped('line_total'))
            
            # Shop Fee (at shop rate - customer rate, $75/hr)
            # Shop labor is tracked but NOT included in customer estimate total
            # shop_fee = estimate.shop_labor_total
            
            # Install Fee (at install rate - customer rate)
            install_fee = estimate.install_total
            
            # Travel Fee
            travel_fee = estimate.travel_total
            
            # Equipment Fee (pass-through)
            equipment_fee = estimate.equipment_total
            
            # =================================================================
            # STORE IN FIELDS
            # =================================================================
            estimate.signage_total = signage
            
            # =================================================================
            # SUBTOTAL & TOTAL (same - no additional markup)
            # =================================================================
            estimate.subtotal = (
                signage +
                install_fee +
                travel_fee +
                equipment_fee
            )
            
            # Total = Subtotal (no additional markup needed)
            estimate.total = estimate.subtotal
            
            # Profitability (internal tracking only)
            # Rough estimate: markup is ~40% of sign price
            estimate.profit_amount = signage * 0.40
            if estimate.total:
                estimate.profit_margin_pct = (estimate.profit_amount / estimate.total) * 100
            else:
                estimate.profit_margin_pct = 0

    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def write(self, vals):
        """
        Override write to sync estimate state with CRM opportunity stage.
        """
        res = super(Estimate, self).write(vals)
        
        # Avoid recursive sync when called from CRM stage change
        if 'state' in vals and not self.env.context.get('skip_crm_sync'):
            self._sync_crm_stage(vals['state'])
        
        return res
    
    def _sync_crm_stage(self, new_state):
        """Sync estimate state changes to CRM opportunity stages"""
        stage_mapping = {
            'approved': 'patriot_crm.stage_bid_prepared',
            'submitted': 'patriot_crm.stage_bid_submitted',
            'won': 'patriot_crm.stage_won',
        }
        
        stage_ref = stage_mapping.get(new_state)
        if stage_ref:
            stage = self.env.ref(stage_ref, raise_if_not_found=False)
            if stage:
                for estimate in self:
                    if estimate.opportunity_id:
                        estimate.opportunity_id.stage_id = stage
                        
                        # If Won, also ensure project is created
                        if new_state == 'won':
                            estimate.opportunity_id._ensure_project_created()
    
    def action_populate_from_sign_types(self):
        """Create estimate lines from opportunity's sign types"""
        self.ensure_one()
        EstimateLine = self.env['ps.estimate.line']
        
        for sign_type in self.opportunity_id.sign_type_ids:
            EstimateLine.create({
                'estimate_id': self.id,
                'sign_type_id': sign_type.id,
                'quantity': sign_type.quantity,
                'sign_width': sign_type.width,
                'sign_height': sign_type.length,
                'material_unit_cost': sign_type.unit_cost or 0,
            })
        
        return True

    def action_submit(self):
        """Mark estimate as submitted"""
        self.write({'state': 'submitted'})

    def action_approve(self):
        """Mark estimate as approved"""
        self.write({'state': 'approved'})
    
    def action_mark_won(self):
        """Mark estimate as won"""
        self.write({'state': 'won'})
    
    def action_mark_lost(self):
        """Mark estimate as lost"""
        self.write({'state': 'lost'})


class EstimateLine(models.Model):
    """
    Estimate Line - Individual line item in an estimate.
    """
    _name = 'ps.estimate.line'
    _description = 'Estimate Line'
    _order = 'sequence, id'

    estimate_id = fields.Many2one(
        'ps.estimate',
        string='Estimate',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    # =========================================================================
    # SIGN TYPE REFERENCE
    # =========================================================================
    sign_type_id = fields.Many2one(
        'ps.sign.type',
        string='Sign Type'
    )
    description = fields.Char(
        string='Description'
    )
    
    # From sign type
    category_id = fields.Many2one(
        related='sign_type_id.category_id',
        string='Category'
    )
    dimensions_display = fields.Char(
        related='sign_type_id.dimensions_display',
        string='Size'
    )
    
    # =========================================================================
    # QUANTITY
    # =========================================================================
    quantity = fields.Integer(
        string='Qty',
        default=1
    )
    uom = fields.Selection([
        ('ea', 'Each'),
        ('sf', 'Sq Ft'),
        ('lf', 'Lin Ft'),
        ('set', 'Set'),
    ], string='UoM', default='ea')
    
    # =========================================================================
    # MATERIAL COSTS
    # =========================================================================
    material_unit_cost = fields.Float(
        string='Material Unit Cost'
    )
    material_extended = fields.Float(
        string='Material Extended',
        compute='_compute_extended',
        store=True
    )
    
    # =========================================================================
    # LABOR COSTS
    # =========================================================================
    labor_hours = fields.Float(
        string='Labor Hours'
    )
    labor_rate = fields.Float(
        string='Labor Rate',
        default=75.0
    )
    labor_extended = fields.Float(
        string='Labor Extended',
        compute='_compute_extended',
        store=True
    )
    
    # =========================================================================
    # INSTALLATION COSTS
    # =========================================================================
    install_hours = fields.Float(
        string='Install Hours'
    )
    install_rate = fields.Float(
        string='Install Rate',
        default=85.0
    )
    install_extended = fields.Float(
        string='Install Extended',
        compute='_compute_extended',
        store=True
    )
    
    # =========================================================================
    # LINE TOTAL
    # =========================================================================
    line_total = fields.Float(
        string='Line Total',
        compute='_compute_extended',
        store=True
    )
    
    # =========================================================================
    # NOTES
    # =========================================================================
    notes = fields.Char(
        string='Notes'
    )

    # =========================================================================
    # COMPUTED
    # =========================================================================
    
    @api.depends('quantity', 'material_unit_cost', 'labor_hours', 'labor_rate',
                 'install_hours', 'install_rate')
    def _compute_extended(self):
        for line in self:
            line.material_extended = line.quantity * line.material_unit_cost
            line.labor_extended = line.labor_hours * line.labor_rate
            line.install_extended = line.install_hours * line.install_rate
            line.line_total = line.material_extended + line.labor_extended + line.install_extended

    @api.onchange('sign_type_id')
    def _onchange_sign_type_id(self):
        """Auto-fill from sign type"""
        if self.sign_type_id:
            self.description = self.sign_type_id.name
            self.quantity = self.sign_type_id.quantity
            if self.sign_type_id.unit_cost:
                self.material_unit_cost = self.sign_type_id.unit_cost


class EstimateLine(models.Model):
    """
    Estimate Line - Individual line item in an estimate.
    
    Includes detailed cost calculation engine for panel signs:
    - Batch optimization (signs per sheet)
    - Waste calculation
    - Mold setup labor
    """
    _name = 'ps.estimate.line'
    _description = 'Estimate Line'
    _order = 'sequence, id'

    estimate_id = fields.Many2one(
        'ps.estimate',
        string='Estimate',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    # =========================================================================
    # SIGN TYPE REFERENCE
    # =========================================================================
    sign_type_id = fields.Many2one(
        'ps.sign.type',
        string='Sign Type'
    )
    description = fields.Char(
        string='Description'
    )
    
    # From sign type
    category_id = fields.Many2one(
        related='sign_type_id.category_id',
        string='Category'
    )
    dimensions_display = fields.Char(
        related='sign_type_id.dimensions_display',
        string='Size'
    )
    
    # Dimension inputs for calc
    sign_width = fields.Float(string='Width (in)')
    sign_height = fields.Float(string='Height (in)')
    
    # =========================================================================
    # QUANTITY & UOM
    # =========================================================================
    quantity = fields.Integer(string='Qty', default=1)
    uom = fields.Selection([
        ('ea', 'Each'),
        ('sf', 'Sq Ft'),
        ('lf', 'Lin Ft'),
        ('set', 'Set'),
    ], string='UoM', default='ea')
    
    # =========================================================================
    # COST CALCULATION ENGINE
    # =========================================================================
    
    # Batch details
    signs_per_mold = fields.Float(string='Signs/Mold', compute='_compute_batch_size', store=True)
    molds_needed = fields.Float(string='Molds Needed', compute='_compute_batch_size', store=True)
    signs_produced = fields.Float(string='Signs Produced', compute='_compute_batch_size', store=True)
    stock_generated = fields.Float(string='Stock Gain', compute='_compute_batch_size', store=True)
    
    # Material Usage
    sheets_needed = fields.Float(string='Sheets Needed', compute='_compute_material_usage', store=True)
    waste_percent = fields.Float(string='Waste %', compute='_compute_material_usage', store=True)
    
    # Cost Details
    material_unit_cost = fields.Float(string='Mat. Cost/Unit', compute='_compute_costs', store=True)
    labor_unit_cost = fields.Float(string='Labor Cost/Unit', compute='_compute_costs', store=True)
    overhead_unit_cost = fields.Float(string='Overhead/Unit', compute='_compute_costs', store=True)
    total_unit_cost = fields.Float(string='Total Cost/Unit', compute='_compute_costs', store=True)
    
    calculate_dynamic = fields.Boolean(string='Dynamic Costing', default=True)
    
    # =========================================================================
    # PRICING
    # =========================================================================
    
    # Labor & Install inputs (for manual override or reference)
    labor_hours = fields.Float(string='Labor Hours', compute='_compute_labor_hours', store=True)
    labor_rate = fields.Float(string='Labor Rate', default=75.0)
    install_hours = fields.Float(string='Install Hours')
    install_rate = fields.Float(string='Install Rate', default=100.0)

    unit_price = fields.Float(string='Unit Price (Sell)', compute='_compute_sell_price', store=True)
    
    material_extended = fields.Float(string='Material Ext.', compute='_compute_extended', store=True)
    labor_extended = fields.Float(string='Labor Ext.', compute='_compute_extended', store=True)
    install_extended = fields.Float(string='Install Ext.', compute='_compute_extended', store=True)
    line_total = fields.Float(string='Line Total', compute='_compute_extended', store=True)
    
    profit_margin = fields.Float(string='Margin %', compute='_compute_margin', store=True)
    breakeven_price = fields.Float(string='Break-Even $', compute='_compute_margin', store=True,
        help='Minimum price per unit to cover all costs (material + labor + overhead)')

    # =========================================================================
    # COMPUTATIONS
    # =========================================================================

    @api.depends('molds_needed')
    def _compute_labor_hours(self):
        """Calculate labor hours from molds: molds × mold_time / 60 (matches Labor & Travel tab)"""
        for line in self:
            mold_time = line.estimate_id.mold_time_minutes or 50.0
            line.labor_hours = (line.molds_needed * mold_time) / 60.0

    @api.depends('sign_width', 'sign_height', 'quantity')
    def _compute_batch_size(self):
        """Calculate optimization of signs on standard press sheet (13x19)"""
        PRESS_W, PRESS_H = 13.0, 19.0
        
        for line in self:
            if not line.sign_width or not line.sign_height:
                line.signs_per_mold = 1.0
                continue
                
            w, h = line.sign_width, line.sign_height
            
            # Optimization logic
            fit1 = int(PRESS_W // w) * int(PRESS_H // h)
            fit2 = int(PRESS_W // h) * int(PRESS_H // w)
            per_mold = max(fit1, fit2, 1)
            
            line.signs_per_mold = per_mold
            
            # Calculate molds needed (rounding up)
            # 17 molds fit on a standard 49x97 sheet
            MOLDS_PER_SHEET = 17
            
            total_signs_capacity = per_mold # signs per 1 mold
            
            # Total molds needed for Quantity
            import math
            molds = math.ceil(line.quantity / per_mold)
            
            line.molds_needed = molds
            line.signs_produced = molds * per_mold
            line.stock_generated = line.signs_produced - line.quantity

    @api.depends('sheets_needed', 'molds_needed', 'quantity', 'calculate_dynamic', 'sign_width', 'sign_height')
    def _compute_material_usage(self):
        """Calculate sheets needed based on molds and true waste %"""
        # Standard sheet sizes (should ideally come from product, but hardcoded for now based on logic)
        SHEET_W, SHEET_H = 49.0, 97.0 # Pionite size
        SHEET_AREA = SHEET_W * SHEET_H
        MOLDS_PER_SHEET = 17
        
        for line in self:
            if not line.molds_needed:
                line.sheets_needed = 0
                line.waste_percent = 0
                continue
                
            # Sheets needed (Pionite)
            # Sheets needed (Pionite) - Fractional usage
            line.sheets_needed = line.molds_needed / MOLDS_PER_SHEET
            
            # True Waste Calculation:
            # Waste = (Total Sheet Area Consumed - Total Sign Area) / Total Sheet Area Consumed
            if line.sign_width and line.sign_height and line.sheets_needed:
                total_sheet_area = line.sheets_needed * SHEET_AREA
                
                # Area actually used by the finished signs
                # Note: We use the quantity ordered, not produced, because the extra signs are "stock" asset, not waste
                # However, the user said "even if you fit 6, that doesn't mean you use full square inch"
                # So waste is the offcut material that goes in the bin.
                total_sign_area = line.quantity * (line.sign_width * line.sign_height)
                
                if total_sheet_area > 0:
                    line.waste_percent = ((total_sheet_area - total_sign_area) / total_sheet_area) * 100
                else:
                    line.waste_percent = 0
            else:
                 # Fallback if dimensions missing
                line.waste_percent = 0

    @api.depends('sheets_needed', 'molds_needed', 'signs_produced', 'quantity', 'calculate_dynamic')
    def _compute_costs(self):
        """Calculate material and labor costs from product catalog"""
        company = self.env.company
        
        # Look up material products from catalog
        Product = self.env['product.product']
        pionite = self.env.ref('patriot_base.product_pionite_sheet', raise_if_not_found=False)
        abs_sheet = self.env.ref('patriot_base.product_abs_18', raise_if_not_found=False)
        ink = self.env.ref('patriot_base.product_ink', raise_if_not_found=False)
        paint = self.env.ref('patriot_base.product_paint', raise_if_not_found=False)
        tape = self.env.ref('patriot_base.product_tape', raise_if_not_found=False)
        mclube = self.env.ref('patriot_base.product_mclube', raise_if_not_found=False)
        mold_labor = self.env.ref('patriot_base.product_mold_labor', raise_if_not_found=False)
        
        # Get costs from products (fall back to 0 if not found)
        pionite_cost = pionite.standard_price if pionite else 211.30
        abs_cost = abs_sheet.standard_price if abs_sheet else 80.00
        ink_cost = ink.standard_price if ink else 0.33
        paint_cost = paint.standard_price if paint else 0.60
        tape_cost = tape.standard_price if tape else 0.25
        mclube_cost = mclube.standard_price if mclube else 0.50
        mold_labor_cost = mold_labor.standard_price if mold_labor else 40.00
        
        for line in self:
            if not line.calculate_dynamic:
                continue
                
            # Material Cost (from product catalog)
            sheet_cost_total = (line.sheets_needed * pionite_cost) + \
                               (line.sheets_needed * abs_cost)
                               
            # Ink & paint applied to every sign produced (including stock)
            signs = line.signs_produced or line.quantity or 1
            consumables = (signs * ink_cost) + \
                          (signs * paint_cost) + \
                          (line.molds_needed * tape_cost) + \
                          (line.molds_needed * mclube_cost)
                          
            total_material = sheet_cost_total + consumables
            
            # Unit Cost Calculation (Standard Costing based on Batch Capacity)
            # Dividing by signs_produced counts the "Stock" items as valid units that absorb cost.
            divisor = line.signs_produced if line.signs_produced else (line.quantity or 1)

            if line.quantity:
                line.material_unit_cost = total_material / divisor
            
            # Labor Cost: mold_time per mold at shop rate (overhead-loaded)
            mold_time = line.estimate_id.mold_time_minutes or 50.0
            shop_rate = line.estimate_id.shop_rate or 85.0
            labor_cost_per_mold = (mold_time / 60.0) * shop_rate
            total_labor = line.molds_needed * labor_cost_per_mold
            
            if line.quantity:
                line.labor_unit_cost = total_labor / divisor
                
            # Overhead
            line.overhead_unit_cost = (line.material_unit_cost + line.labor_unit_cost) * \
                                      (company.pricing_overhead_pct / 100.0)
                                      
            line.total_unit_cost = line.material_unit_cost + line.labor_unit_cost + line.overhead_unit_cost

    def _get_size_price(self, sqin):
        """
        Size-based reference pricing: monotonically increasing with area.
        
        Uses a reference price table approach:
          - 6×6 (36 sqin) = $55 GC base price
          - Price scales by square footage relative to 6×6
          - Larger signs always cost more (guaranteed monotonic)
        
        Currently fitted to GC prices:
          6×6 → $55,  8×8 → $65
        
        Future: add trade pricing tier, adjust SIZE_FACTOR with more data.
        """
        # =====================================================================
        # REFERENCE PRICING CONSTANTS
        # Adjust these as more pricing data becomes available
        # =====================================================================
        REF_SIZE_SQIN = 36.0   # 6×6 = 36 sq in (reference size)
        REF_PRICE = 55.0       # GC price for 6×6
        MIN_PRICE = 35.0       # Floor for very small signs
        SIZE_FACTOR = 0.22     # Controls how fast price grows with size
        
        if sqin <= REF_SIZE_SQIN:
            # Small signs: scale down linearly from reference
            raw_price = REF_PRICE * (sqin / REF_SIZE_SQIN)
        else:
            # Larger signs: scale up with diminishing returns
            ratio = sqin / REF_SIZE_SQIN
            raw_price = REF_PRICE * (1 + (ratio - 1) * SIZE_FACTOR)
        
        return max(raw_price, MIN_PRICE)

    @api.depends('total_unit_cost', 'calculate_dynamic', 'sign_width', 'sign_height')
    def _compute_sell_price(self):
        """
        Hybrid pricing: max(cost_floor, size_price), rounded to nearest $5.
        
        - cost_floor: break-even × minimum margin (never sell below cost)
        - size_price: reference price based on square inches (always monotonic)
        - Final price is whichever is HIGHER
        """
        ROUND_TO = 5.0
        MIN_MARGIN = 1.15  # 15% above break-even minimum
        
        for line in self:
            if line.calculate_dynamic and line.total_unit_cost:
                sqin = (line.sign_width or 6) * (line.sign_height or 6)
                
                # Two pricing signals:
                cost_floor = line.total_unit_cost * MIN_MARGIN   # never sell below cost
                size_price = self._get_size_price(sqin)          # market-rate by size
                
                # Take the higher of the two
                raw_price = max(cost_floor, size_price)
                line.unit_price = round(raw_price / ROUND_TO) * ROUND_TO
            else:
                line.unit_price = 0.0

    @api.depends('quantity', 'unit_price', 'material_unit_cost', 'labor_unit_cost', 'install_hours', 'install_rate')
    def _compute_extended(self):
        for line in self:
            # Extended costs
            line.material_extended = line.quantity * line.material_unit_cost
            line.labor_extended = line.quantity * line.labor_unit_cost
            
            # Install cost from hours
            if line.install_hours:
                line.install_extended = line.install_hours * line.install_rate
            else:
                line.install_extended = 0.0 
            
            # Line total is PRICE, not cost
            line.line_total = line.quantity * line.unit_price

    @api.depends('unit_price', 'total_unit_cost')
    def _compute_margin(self):
        for line in self:
            line.breakeven_price = line.total_unit_cost
            if line.unit_price:
                line.profit_margin = ((line.unit_price - line.total_unit_cost) / line.unit_price) * 100
            else:
                line.profit_margin = 0

    @api.onchange('sign_type_id')
    def _onchange_sign_type_id(self):
        if self.sign_type_id:
            self.description = self.sign_type_id.name
            self.quantity = self.sign_type_id.quantity
            self.sign_width = self.sign_type_id.width
            self.sign_height = self.sign_type_id.length
            # If sign type already has a calculated unit cost, we could use it, 
            # but we recalculate here to ensure estimate-specific logic applies.
            # self.sign_width = ...
