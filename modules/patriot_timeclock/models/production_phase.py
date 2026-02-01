# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductionPhase(models.Model):
    """
    Production Phase - Master data for sign manufacturing workflow phases.
    
    Phases define the stages of work: Design, Fab, Sand, Pack, Install, etc.
    Tasks are linked to phases to categorize work.
    """
    _name = 'ps.production.phase'
    _description = 'Production Phase'
    _order = 'sequence, id'

    name = fields.Char(
        string='Phase Name',
        required=True,
        translate=True,
        help='Name of the production phase'
    )
    code = fields.Char(
        string='Code',
        help='Short code for the phase (e.g., FAB, SAND, PACK)'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order in the production workflow'
    )
    color = fields.Integer(
        string='Color',
        default=0,
        help='Color index for kanban views'
    )
    description = fields.Text(
        string='Description',
        help='Detailed description of this phase'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    # For future ML estimation
    default_hours_per_sign = fields.Float(
        string='Default Hours/Sign',
        default=0.0,
        help='Default estimated hours per sign (baseline for learning)'
    )
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Phase code must be unique!'),
    ]
