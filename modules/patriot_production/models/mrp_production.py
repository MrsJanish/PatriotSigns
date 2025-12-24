# -*- coding: utf-8 -*-
from odoo import models, fields


class MrpProduction(models.Model):
    """
    MRP Production extension for sign manufacturing.
    """
    _inherit = 'mrp.production'

    # Link to Patriot Signs production order
    ps_production_order_id = fields.Many2one(
        'ps.production.order',
        string='PS Production Order',
        help='Link to Patriot Signs production order'
    )
    
    # Link to project for context
    ps_project_id = fields.Many2one(
        related='ps_production_order_id.project_id',
        string='Sign Project',
        store=True
    )
