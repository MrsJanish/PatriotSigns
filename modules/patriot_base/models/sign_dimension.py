# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SignDimension(models.Model):
    """
    Sign Dimension - Standardized dimension lookup table.
    
    Prevents data inconsistencies like "6x8" vs "6 x 8" vs "6\" x 8\""
    All dimensions stored as numeric inches with computed display strings.
    """
    _name = 'sign.dimension'
    _description = 'Sign Dimension'
    _order = 'square_inches, name'

    name = fields.Char(
        string='Display Name',
        compute='_compute_name',
        store=True,
        help='Auto-generated display name like "8 x 6"'
    )
    
    # Core dimensions (always in inches)
    width_in = fields.Float(
        string='Width (inches)',
        required=True,
        help='Width in inches'
    )
    height_in = fields.Float(
        string='Height (inches)',
        required=True,
        help='Height in inches'
    )
    depth_in = fields.Float(
        string='Depth (inches)',
        default=0,
        help='Depth/thickness in inches (optional)'
    )
    
    # Round signs
    can_be_round = fields.Boolean(
        string='Can Be Round',
        default=False,
        help='If checked, this dimension can represent a diameter'
    )
    diameter = fields.Float(
        string='Diameter (inches)',
        help='Diameter for round signs'
    )
    
    # Computed values
    square_inches = fields.Float(
        string='Square Inches',
        compute='_compute_square_inches',
        store=True,
        help='Total area in square inches'
    )
    
    # Display formats
    display_by_inch = fields.Char(
        string='Display (inches)',
        compute='_compute_displays',
        store=True,
        help='Format: 8 x 6'
    )
    display_by_feet_inch = fields.Char(
        string='Display (feet/inches)',
        compute='_compute_displays',
        store=True,
        help='Format: 2\'-6" x 1\'-8"'
    )
    display_diameter = fields.Char(
        string='Display (diameter)',
        compute='_compute_displays',
        store=True,
        help='Format: Ø 24"'
    )
    
    # Organization
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    # Usage tracking
    usage_count = fields.Integer(
        string='Usage Count',
        compute='_compute_usage_count',
        help='Number of sign types using this dimension'
    )

    _sql_constraints = [
        ('unique_dimensions', 
         'UNIQUE(width_in, height_in, depth_in)', 
         'This dimension combination already exists!')
    ]

    @api.depends('width_in', 'height_in', 'depth_in')
    def _compute_name(self):
        for record in self:
            if record.width_in and record.height_in:
                # Format as integers if whole numbers
                w = int(record.width_in) if record.width_in == int(record.width_in) else record.width_in
                h = int(record.height_in) if record.height_in == int(record.height_in) else record.height_in
                if record.depth_in:
                    d = int(record.depth_in) if record.depth_in == int(record.depth_in) else record.depth_in
                    record.name = f"{w} x {h} x {d}"
                else:
                    record.name = f"{w} x {h}"
            elif record.diameter:
                d = int(record.diameter) if record.diameter == int(record.diameter) else record.diameter
                record.name = f"Ø {d}"
            else:
                record.name = "Undefined"

    @api.depends('width_in', 'height_in', 'diameter', 'can_be_round')
    def _compute_square_inches(self):
        import math
        for record in self:
            if record.can_be_round and record.diameter:
                # Circle area
                record.square_inches = math.pi * (record.diameter / 2) ** 2
            elif record.width_in and record.height_in:
                record.square_inches = record.width_in * record.height_in
            else:
                record.square_inches = 0

    @api.depends('width_in', 'height_in', 'diameter')
    def _compute_displays(self):
        for record in self:
            # Display by inches
            if record.width_in and record.height_in:
                w = int(record.width_in) if record.width_in == int(record.width_in) else record.width_in
                h = int(record.height_in) if record.height_in == int(record.height_in) else record.height_in
                record.display_by_inch = f"{w} x {h}"
            else:
                record.display_by_inch = ""
            
            # Display by feet/inches
            if record.width_in and record.height_in:
                def to_feet_inches(inches):
                    feet = int(inches // 12)
                    remaining = inches % 12
                    if feet > 0 and remaining > 0:
                        return f"{feet}'-{int(remaining)}\""
                    elif feet > 0:
                        return f"{feet}'-0\""
                    else:
                        return f"{int(remaining)}\""
                
                record.display_by_feet_inch = f"{to_feet_inches(record.width_in)} x {to_feet_inches(record.height_in)}"
            else:
                record.display_by_feet_inch = ""
            
            # Display diameter
            if record.diameter:
                d = int(record.diameter) if record.diameter == int(record.diameter) else record.diameter
                record.display_diameter = f"Ø {d}\""
            else:
                record.display_diameter = ""

    def _compute_usage_count(self):
        """Count how many sign types use this dimension"""
        # Will be updated when ps.sign.type is created
        for record in self:
            record.usage_count = 0

    @api.model
    def find_or_create(self, width, height, depth=0):
        """Find existing dimension or create new one"""
        dimension = self.search([
            ('width_in', '=', width),
            ('height_in', '=', height),
            ('depth_in', '=', depth),
        ], limit=1)
        
        if not dimension:
            dimension = self.create({
                'width_in': width,
                'height_in': height,
                'depth_in': depth,
            })
        
        return dimension
