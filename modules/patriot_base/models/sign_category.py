# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SignCategory(models.Model):
    """
    Sign Category - Global classification for sign types.
    
    Examples: Panel/ADA, Plaques, Directional Channel Letters, Monument
    These categories are reusable across all projects.
    """
    _name = 'sign.category'
    _description = 'Sign Category'
    _order = 'sequence, name'

    name = fields.Char(
        string='Category Name',
        required=True,
        help='Full category name, e.g., "Panel / ADA", "Plaques"'
    )
    code = fields.Char(
        string='Code',
        required=True,
        help='Short code, e.g., PAN, PLQ, DCHA'
    )
    description = fields.Text(
        string='Description',
        help='Detailed description of this category'
    )
    
    # Visual
    color = fields.Integer(
        string='Color',
        default=0,
        help='Kanban color index for visual grouping'
    )
    
    # Defaults
    is_ada_default = fields.Boolean(
        string='ADA by Default',
        default=False,
        help='If checked, sign types in this category default to ADA compliant'
    )
    is_interior_default = fields.Boolean(
        string='Interior by Default',
        default=True,
        help='If checked, sign types in this category default to interior signs'
    )
    
    # Organization
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Ordering sequence'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Uncheck to archive this category'
    )
    
    # Relationships
    subtype_ids = fields.One2many(
        'sign.subtype',
        'category_id',
        string='Subtypes'
    )
    subtype_count = fields.Integer(
        string='Subtype Count',
        compute='_compute_subtype_count'
    )

    # Odoo 19 constraint format
    _unique_code = models.Constraint(
        'UNIQUE(code)',
        'Category code must be unique!'
    )

    @api.depends('subtype_ids')
    def _compute_subtype_count(self):
        for record in self:
            record.subtype_count = len(record.subtype_ids)

    def name_get(self):
        """Display as 'CODE - Name'"""
        result = []
        for record in self:
            name = f"{record.code} - {record.name}" if record.code else record.name
            result.append((record.id, name))
        return result
