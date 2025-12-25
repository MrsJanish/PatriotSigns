# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SignType(models.Model):
    """
    Sign Type - Project-specific sign type definition.
    
    Each sign type belongs to ONE project (crm.lead) and represents a 
    specific sign configuration (e.g., "Type A" = 6x8 ADA Room Sign).
    
    IMPORTANT: Sign Type "A" in Project 1 is completely different from
    Sign Type "A" in Project 2. This is by design per architect convention.
    """
    _name = 'ps.sign.type'
    _description = 'Sign Type'
    _order = 'opportunity_id, sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # =========================================================================
    # IDENTIFICATION
    # =========================================================================
    name = fields.Char(
        string='Sign Type ID',
        required=True,
        tracking=True,
        help="Architect's designation: A, B, SN-1, RID-1, etc."
    )
    opportunity_id = fields.Many2one(
        'crm.lead',
        string='Project',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    project_alias = fields.Char(
        related='opportunity_id.project_alias',
        string='Project Alias',
        store=True
    )
    
    # =========================================================================
    # TEMPLATE (for quick-add)
    # =========================================================================
    template_id = fields.Many2one(
        'ps.sign.type.template',
        string='Template',
        help='Select a template to auto-fill dimensions and category'
    )
    
    @api.onchange('template_id')
    def _onchange_template_id(self):
        """Auto-fill fields from selected template"""
        if self.template_id:
            template = self.template_id
            self.category_id = template.category_id
            self.width = template.width
            self.length = template.length
            self.unit_price = template.default_unit_price
            self.is_ada = template.is_ada
            if not self.name:
                self.name = template.name
            # Increment usage counter
            template.sudo().write({'use_count': template.use_count + 1})
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    description = fields.Text(
        string='Description'
    )

    # =========================================================================
    # CLASSIFICATION
    # =========================================================================
    category_id = fields.Many2one(
        'sign.category',
        string='Category',
        tracking=True
    )
    category_code = fields.Char(
        related='category_id.code',
        string='Category Code',
        store=True
    )
    subtype_id = fields.Many2one(
        'sign.subtype',
        string='Subtype'
    )

    # =========================================================================
    # DIMENSIONS (Numeric - not text!)
    # =========================================================================
    dimension_id = fields.Many2one(
        'sign.dimension',
        string='Standard Size',
        help='Select from standard dimensions or enter custom'
    )
    length = fields.Float(
        string='Length (in)',
        tracking=True
    )
    width = fields.Float(
        string='Width (in)',
        tracking=True
    )
    depth = fields.Float(
        string='Depth (in)'
    )
    is_round = fields.Boolean(
        string='Round Shape',
        default=False
    )
    diameter = fields.Float(
        string='Diameter (in)'
    )
    dimensions_display = fields.Char(
        string='Dimensions',
        compute='_compute_dimensions_display',
        store=True
    )
    square_inches = fields.Float(
        string='Square Inches',
        compute='_compute_square_inches',
        store=True
    )

    # =========================================================================
    # PHYSICAL SPECIFICATIONS (Selection fields - not text!)
    # =========================================================================
    material = fields.Selection([
        ('aluminum', 'Aluminum'),
        ('acrylic', 'Acrylic'),
        ('pvc', 'PVC/Sintra'),
        ('photopolymer', 'Photopolymer'),
        ('brass', 'Brass'),
        ('stainless', 'Stainless Steel'),
        ('wood', 'Wood'),
        ('hdpe', 'HDPE'),
        ('dibond', 'Dibond/ACM'),
        ('other', 'Other'),
    ], string='Material', tracking=True)
    
    finish = fields.Selection([
        ('matte', 'Matte'),
        ('satin', 'Satin'),
        ('gloss', 'Gloss'),
        ('brushed', 'Brushed'),
        ('textured', 'Textured'),
        ('painted', 'Painted'),
        ('woodgrain', 'Woodgrain Laminate'),
        ('custom', 'Custom'),
    ], string='Finish')
    
    finish_color = fields.Char(
        string='Finish Color',
        help='Color name or code'
    )
    
    mounting = fields.Selection([
        ('wall', 'Wall Mounted'),
        ('projecting', 'Projecting/Flag'),
        ('ceiling', 'Ceiling Hung'),
        ('post', 'Post Mounted'),
        ('freestanding', 'Freestanding'),
        ('monument', 'Monument'),
        ('window', 'Window/Glass Applied'),
        ('standoff', 'Standoff Mounted'),
    ], string='Mounting Method')
    
    mounting_height = fields.Float(
        string='Mounting Height (in)',
        help='Height above finished floor to center of sign'
    )

    # =========================================================================
    # ADA COMPLIANCE
    # =========================================================================
    is_ada = fields.Boolean(
        string='ADA Sign',
        default=False,
        tracking=True
    )
    has_tactile = fields.Boolean(
        string='Tactile Characters',
        default=False
    )
    has_braille = fields.Boolean(
        string='Braille',
        default=False
    )
    has_pictogram = fields.Boolean(
        string='Pictogram',
        default=False
    )
    pictogram_type = fields.Char(
        string='Pictogram Type'
    )

    # =========================================================================
    # WINDOW/INSERT
    # =========================================================================
    has_window = fields.Boolean(
        string='Has Window',
        default=False
    )
    window_width = fields.Float(
        string='Window Width (in)'
    )
    window_height = fields.Float(
        string='Window Height (in)'
    )

    # =========================================================================
    # ILLUMINATION
    # =========================================================================
    is_illuminated = fields.Boolean(
        string='Illuminated',
        default=False
    )
    illumination_type = fields.Selection([
        ('none', 'Non-Illuminated'),
        ('internal', 'Internally Illuminated'),
        ('external', 'Externally Illuminated'),
        ('edge', 'Edge-Lit'),
        ('halo', 'Halo-Lit'),
        ('channel', 'Channel Letters'),
    ], string='Illumination Type', default='none')

    # =========================================================================
    # QUANTITY
    # =========================================================================
    quantity = fields.Integer(
        string='Quantity',
        default=1,
        tracking=True
    )
    qty_source = fields.Selection([
        ('plans', 'Counted from Plans'),
        ('schedule', 'From Sign Schedule'),
        ('estimate', 'Estimated'),
        ('changed', 'Changed After Bid'),
    ], string='Qty Source', default='plans')

    # =========================================================================
    # CONTENT
    # =========================================================================
    has_custom_copy = fields.Boolean(
        string='Custom Copy',
        default=False
    )
    letter_height = fields.Float(
        string='Letter Height (in)'
    )
    letter_count = fields.Integer(
        string='Letter Count'
    )
    notes = fields.Text(
        string='Notes'
    )

    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    instance_ids = fields.One2many(
        'ps.sign.instance',
        'sign_type_id',
        string='Sign Instances'
    )
    instance_count = fields.Integer(
        string='Instances',
        compute='_compute_instance_count',
        store=True
    )
    bookmark_ids = fields.One2many(
        'ps.sign.bookmark',
        'sign_type_id',
        string='Bookmarks'
    )
    bookmark_count = fields.Integer(
        string='Bookmarks',
        compute='_compute_bookmark_count'
    )

    # =========================================================================
    # COSTING
    # =========================================================================
    unit_cost = fields.Float(
        string='Unit Cost',
        tracking=True
    )
    unit_price = fields.Float(
        string='Unit Price',
        tracking=True
    )
    install_rate = fields.Float(
        string='Install Rate'
    )
    extended_price = fields.Float(
        string='Extended Price',
        compute='_compute_extended_price',
        store=True
    )

    # =========================================================================
    # STATUS
    # =========================================================================
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('ordered', 'Ordered'),
        ('production', 'In Production'),
        ('complete', 'Complete'),
        ('canceled', 'Canceled'),
    ], string='Status', default='draft', tracking=True)
    
    confirmed = fields.Boolean(
        string='Confirmed for Schedule',
        default=False
    )

    # =========================================================================
    # SUPPLIER
    # =========================================================================
    supplier_id = fields.Many2one(
        'res.partner',
        string='Supplier',
        domain="[('is_sign_supplier', '=', True)]"
    )

    # =========================================================================
    # VARIANTS & COMPONENTS
    # =========================================================================
    is_variant = fields.Boolean(
        string='Is Variant',
        default=False
    )
    variant_of_id = fields.Many2one(
        'ps.sign.type',
        string='Variant Of',
        domain="[('opportunity_id', '=', opportunity_id)]"
    )
    is_component = fields.Boolean(
        string='Is Component',
        default=False
    )
    component_of_id = fields.Many2one(
        'ps.sign.type',
        string='Component Of',
        domain="[('opportunity_id', '=', opportunity_id)]"
    )
    is_backer = fields.Boolean(
        string='Is Backer',
        default=False
    )
    backer_id = fields.Many2one(
        'ps.sign.type',
        string='Backer Sign Type',
        domain="[('opportunity_id', '=', opportunity_id), ('is_backer', '=', True)]"
    )

    # =========================================================================
    # TRACKING
    # =========================================================================
    added_post_bid = fields.Boolean(
        string='Added Post-Bid',
        default=False
    )
    replaced_by_id = fields.Many2one(
        'ps.sign.type',
        string='Replaced By',
        domain="[('opportunity_id', '=', opportunity_id)]"
    )

    # =========================================================================
    # CONSTRAINTS
    # =========================================================================
    _sql_constraints = [
        ('unique_sign_type_per_project',
         'UNIQUE(opportunity_id, name)',
         'Sign Type ID must be unique within a project!')
    ]

    # =========================================================================
    # COMPUTED FIELDS
    # =========================================================================
    
    @api.depends('length', 'width', 'is_round', 'diameter')
    def _compute_dimensions_display(self):
        for record in self:
            if record.is_round and record.diameter:
                d = int(record.diameter) if record.diameter == int(record.diameter) else record.diameter
                record.dimensions_display = f"Ø {d}\""
            elif record.length and record.width:
                l = int(record.length) if record.length == int(record.length) else record.length
                w = int(record.width) if record.width == int(record.width) else record.width
                record.dimensions_display = f'{l}" x {w}"'
            else:
                record.dimensions_display = ''

    @api.depends('length', 'width', 'is_round', 'diameter')
    def _compute_square_inches(self):
        import math
        for record in self:
            if record.is_round and record.diameter:
                record.square_inches = math.pi * (record.diameter / 2) ** 2
            elif record.length and record.width:
                record.square_inches = record.length * record.width
            else:
                record.square_inches = 0

    @api.depends('instance_ids')
    def _compute_instance_count(self):
        for record in self:
            record.instance_count = len(record.instance_ids)

    @api.depends('bookmark_ids')
    def _compute_bookmark_count(self):
        for record in self:
            record.bookmark_count = len(record.bookmark_ids)

    @api.depends('unit_price', 'quantity')
    def _compute_extended_price(self):
        for record in self:
            record.extended_price = record.unit_price * record.quantity

    # =========================================================================
    # ONCHANGE
    # =========================================================================
    
    @api.onchange('dimension_id')
    def _onchange_dimension_id(self):
        """Auto-fill dimensions from selected standard dimension"""
        if self.dimension_id:
            self.length = self.dimension_id.width_in
            self.width = self.dimension_id.height_in
            if self.dimension_id.depth_in:
                self.depth = self.dimension_id.depth_in

    @api.onchange('category_id')
    def _onchange_category_id(self):
        """Set defaults from category"""
        if self.category_id:
            if self.category_id.is_ada_default:
                self.is_ada = True
                self.has_tactile = True
                self.has_braille = True

    @api.onchange('subtype_id')
    def _onchange_subtype_id(self):
        """Set defaults from subtype"""
        if self.subtype_id:
            if self.subtype_id.is_ada:
                self.is_ada = True
            if self.subtype_id.has_window_default:
                self.has_window = True
            if self.subtype_id.is_illuminated_default:
                self.is_illuminated = True
                self.illumination_type = 'internal'

    @api.onchange('is_ada')
    def _onchange_is_ada(self):
        """When ADA is checked, default tactile and braille"""
        if self.is_ada:
            self.has_tactile = True
            self.has_braille = True

    @api.onchange('length', 'width', 'quantity', 'is_ada', 'category_id')
    def _onchange_compute_price(self):
        """
        Auto-calculate unit price based on dimensions, category, and quantity.
        
        Formula from patriot_estimating:
        1. Calculate material cost per unit (based on sheet usage)
        2. Add labor cost per unit
        3. Add 15% overhead
        4. Multiply by markup (2.4x)
        5. Round to nearest $5
        """
        if not self.length or not self.width:
            return
            
        import math
        
        # Constants from the estimating module
        PRESS_W, PRESS_H = 13.0, 19.0  # Press sheet size
        SHEET_W, SHEET_H = 49.0, 97.0  # Pionite sheet size
        MOLDS_PER_SHEET = 17
        
        # Costs (from product catalog defaults)
        PIONITE_COST = 211.30  # Per sheet
        ABS_COST = 80.00       # Per sheet
        INK_COST = 0.33        # Per sign
        PAINT_COST = 0.60      # Per sign
        TAPE_COST = 0.25       # Per mold
        MCLUBE_COST = 0.50     # Per mold
        EMPLOYEE_WAGE = 10.00  # $/hr
        MOLD_TIME_MINUTES = 80  # Worst case per mold
        
        OVERHEAD_PCT = 15.0
        MARKUP = 2.4
        ROUND_TO = 5.0
        
        # Calculate how many signs fit per mold (optimize rotation)
        w, h = self.width, self.length
        fit1 = int(PRESS_W // w) * int(PRESS_H // h) if w > 0 and h > 0 else 1
        fit2 = int(PRESS_W // h) * int(PRESS_H // w) if w > 0 and h > 0 else 1
        signs_per_mold = max(fit1, fit2, 1)
        
        # Calculate molds needed
        qty = self.quantity or 1
        molds_needed = math.ceil(qty / signs_per_mold)
        
        # Sheets needed
        # Sheets needed - Use fractional sheets (consumption based)
        sheets_needed = molds_needed / MOLDS_PER_SHEET
        
        # Material cost
        sheet_cost = sheets_needed * (PIONITE_COST + ABS_COST)
        consumables = (qty * INK_COST) + (qty * PAINT_COST) + \
                      (molds_needed * TAPE_COST) + (molds_needed * MCLUBE_COST)
        total_material = sheet_cost + consumables
        material_per_unit = total_material / qty if qty else 0
        
        # Labor cost
        labor_per_mold = (MOLD_TIME_MINUTES / 60.0) * EMPLOYEE_WAGE  # ~$13.33
        total_labor = molds_needed * labor_per_mold
        labor_per_unit = total_labor / qty if qty else 0
        
        # Overhead
        overhead_per_unit = (material_per_unit + labor_per_unit) * (OVERHEAD_PCT / 100.0)
        
        # Total cost per unit
        total_cost_per_unit = material_per_unit + labor_per_unit + overhead_per_unit
        
        # Apply markup and round
        raw_price = total_cost_per_unit * MARKUP
        rounded_price = round(raw_price / ROUND_TO) * ROUND_TO
        
        # Set unit cost and unit price
        self.unit_cost = round(total_cost_per_unit, 2)
        self.unit_price = rounded_price

    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def action_confirm(self):
        """Mark sign type as confirmed"""
        self.write({'state': 'confirmed', 'confirmed': True})

    def action_view_instances(self):
        """Open sign instances for this type"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Instances - {self.name}',
            'res_model': 'ps.sign.instance',
            'view_mode': 'list,form',
            'domain': [('sign_type_id', '=', self.id)],
            'context': {'default_sign_type_id': self.id},
        }

    def action_view_bookmarks(self):
        """Open PDF viewer at first bookmark"""
        self.ensure_one()
        if self.bookmark_ids:
            first = self.bookmark_ids[0]
            return {
                'type': 'ir.actions.client',
                'tag': 'cc_ops_pdf_viewer',
                'params': {
                    'attachmentId': first.attachment_id.id,
                    'opportunityId': self.opportunity_id.id,
                    'goToPage': first.page_number,
                },
            }
        return {'type': 'ir.actions.act_window_close'}
