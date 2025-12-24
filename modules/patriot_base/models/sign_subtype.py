# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SignSubtype(models.Model):
    """
    Sign Subtype - Reusable templates for sign variations within categories.
    
    Examples: "Room Num, Insert", "Evacuation Plan", "Directional, Custom"
    These define default characteristics that can be applied to project sign types.
    """
    _name = 'sign.subtype'
    _description = 'Sign Subtype'
    _order = 'category_id, sequence, name'

    name = fields.Char(
        string='Subtype Name',
        required=True,
        help='Display name, e.g., "Room Num, Insert", "Evacuation Plan"'
    )
    code = fields.Char(
        string='Code',
        help='Short code, e.g., RNI, EVAC'
    )
    
    # Classification
    category_id = fields.Many2one(
        'sign.category',
        string='Default Category',
        help='Default category for this subtype'
    )
    category_code = fields.Char(
        related='category_id.code',
        string='Category Code',
        store=True
    )
    
    # Description
    description = fields.Text(
        string='Description',
        help='Detailed description of this subtype'
    )
    
    # ADA Requirements
    is_ada = fields.Boolean(
        string='ADA Compliant',
        default=False,
        help='This subtype is typically ADA compliant'
    )
    requires_braille = fields.Boolean(
        string='Requires Braille',
        default=False,
        help='This subtype typically requires braille'
    )
    requires_pictogram = fields.Boolean(
        string='Requires Pictogram',
        default=False,
        help='This subtype typically requires a pictogram'
    )
    
    # Default Characteristics
    has_window_default = fields.Boolean(
        string='Has Window by Default',
        default=False
    )
    is_illuminated_default = fields.Boolean(
        string='Illuminated by Default',
        default=False
    )
    
    # Default Copy Lines (for signs with standard text patterns)
    default_copy_pattern = fields.Char(
        string='Default Copy Pattern',
        help='Pattern for default copy, e.g., "[room_name]" or "[per drawing]"'
    )
    
    # Setup Status
    setup_status = fields.Selection([
        ('draft', 'Draft'),
        ('completed', 'Completed'),
    ], string='Setup Status', default='draft')
    
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
        help='Number of sign types using this subtype'
    )

    def _compute_usage_count(self):
        """Count how many sign types use this subtype"""
        # Will be updated when ps.sign.type is created
        for record in self:
            record.usage_count = 0

    def name_get(self):
        """Display name with category"""
        result = []
        for record in self:
            if record.display_name_custom:
                name = record.display_name_custom
            else:
                name = record.name.replace('_', ' ')
            if record.category_code:
                name = f"[{record.category_code}] {name}"
            result.append((record.id, name))
        return result
