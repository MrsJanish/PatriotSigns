# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SignPart(models.Model):
    """
    Sign Part - A specific physical component of a Sign Instance.
    
    Examples:
    - "Acetate Face" (Router -> Print)
    - "Aluminum Backer" (Waterjet -> Paint)
    - "Braille Bead" (Assembly)
    
    This allows the Shop Floor to track specific production steps for 
    components rather than just the whole sign.
    """
    _name = 'ps.sign.part'
    _description = 'Sign Part'
    _order = 'instance_id, sequence'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # =========================================================================
    # IDENTIFICATION
    # =========================================================================
    name = fields.Char(
        string='Part Name',
        required=True,
        default='Main Body'
    )
    instance_id = fields.Many2one(
        'ps.sign.instance',
        string='Sign Instance',
        required=True,
        ondelete='cascade',
        index=True
    )
    sign_type_id = fields.Many2one(
        related='instance_id.sign_type_id',
        string='Sign Type',
        store=True,
        readonly=True
    )
    project_id = fields.Many2one(
        related='instance_id.opportunity_id',
        string='Project',
        store=True,
        readonly=True
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    # =========================================================================
    # MANUFACTURING SPECS
    # =========================================================================
    material = fields.Char(
        string='Material',
        help='e.g., .125" Alum, .25" Acrylic'
    )
    process_route = fields.Selection([
        ('router', 'Router'),
        ('laser', 'Laser'),
        ('print', 'Digital Print'),
        ('paint', 'Paint'),
        ('assembly', 'Assembly'),
        ('vinyl', 'Vinyl Plotter'),
        ('purchase', 'Purchased/Buyout'),
    ], string='Primary Process', default='router')
    
    finish_color = fields.Char(
        string='Finish/Color'
    )
    
    # =========================================================================
    # DIMENSIONS
    # =========================================================================
    width = fields.Float(string='Width')
    height = fields.Float(string='Height')
    thickness = fields.Float(string='Thickness')

    # =========================================================================
    # PRODUCTION STATUS
    # =========================================================================
    state = fields.Selection([
        ('draft', 'Pending'),
        ('ready', 'Ready for Production'),
        ('in_progress', 'In Progress'),
        ('quality_check', 'QC Check'),
        ('complete', 'Complete'),
        ('scrap', 'Scrap/Fail'),
    ], string='Status', default='draft', tracking=True)
    
    production_notes = fields.Text(string='Shop Notes')
    
    # Link to Production Batch (The "Work Order")
    production_order_id = fields.Many2one(
        'ps.production.order',
        string='Production Order',
        help='The batch this part is being made in'
    )

    # =========================================================================
    # ACTIONS
    # =========================================================================
    def action_start(self):
        self.write({'state': 'in_progress'})
        
    def action_complete(self):
        self.write({'state': 'complete'})
