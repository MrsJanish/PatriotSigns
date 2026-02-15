# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Crew(models.Model):
    """
    Crew - Installation crew/team.
    """
    _name = 'ps.crew'
    _description = 'Installation Crew'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Crew Name',
        required=True
    )
    code = fields.Char(
        string='Code',
        help='Short code (e.g., CREW-A)'
    )
    
    # Members
    lead_id = fields.Many2one(
        'hr.employee',
        string='Crew Lead'
    )
    member_ids = fields.Many2many(
        'res.users',
        'ps_crew_member_rel',
        'crew_id',
        'user_id',
        string='Members'
    )
    member_count = fields.Integer(
        string='Member Count',
        compute='_compute_member_count'
    )
    
    # Capabilities
    has_lift_cert = fields.Boolean(
        string='Lift Certified',
        default=False
    )
    has_osha_cert = fields.Boolean(
        string='OSHA Certified',
        default=False
    )
    
    # Vehicle
    vehicle = fields.Char(
        string='Vehicle'
    )
    vehicle_capacity = fields.Char(
        string='Vehicle Capacity'
    )
    
    # Status
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    notes = fields.Text(
        string='Notes'
    )

    # =========================================================================
    # COMPUTED
    # =========================================================================
    
    @api.depends('member_ids')
    def _compute_member_count(self):
        for crew in self:
            crew.member_count = len(crew.member_ids)
