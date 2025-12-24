# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SignTypeTemplate(models.Model):
    """
    Sign Type Template - Reusable templates for common sign types.
    
    Select a template when adding sign types to quickly fill in
    standard dimensions, category, and other defaults.
    """
    _name = 'ps.sign.type.template'
    _description = 'Sign Type Template'
    _order = 'sequence, name'

    name = fields.Char(
        string='Template Name',
        required=True,
        help="e.g., 'Room ID 8x8', 'ADA Restroom 6x9', 'Wayfinding 12x18'"
    )
    code = fields.Char(
        string='Code',
        help="Short code for quick reference"
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    # Category
    category_id = fields.Many2one(
        'sign.category',
        string='Category',
        required=True
    )
    
    # Default Dimensions
    width = fields.Float(
        string='Default Width (in)',
        required=True
    )
    length = fields.Float(
        string='Default Length (in)',
        required=True
    )
    
    # Pricing
    default_unit_price = fields.Float(
        string='Default Unit Price',
        help='Suggested unit price for this sign type'
    )
    
    # ADA
    is_ada = fields.Boolean(
        string='ADA Compliant',
        default=False
    )
    has_tactile = fields.Boolean(
        string='Has Tactile',
        default=False
    )
    has_braille = fields.Boolean(
        string='Has Braille',
        default=False
    )
    
    # Description
    description = fields.Text(
        string='Description'
    )
    
    # Usage tracking
    use_count = fields.Integer(
        string='Times Used',
        default=0,
        readonly=True
    )
