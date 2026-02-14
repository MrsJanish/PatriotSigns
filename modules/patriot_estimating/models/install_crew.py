# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CrewEstimating(models.Model):
    """Extend ps.crew with billing members and combined rate."""
    _inherit = 'ps.crew'

    billing_member_ids = fields.One2many(
        'ps.crew.member', 'crew_id',
        string='Billing Members',
    )
    combined_rate = fields.Float(
        string='Combined Rate ($/hr)',
        compute='_compute_combined_rate',
        store=True,
        help='Sum of all member hourly rates',
    )

    @api.depends('billing_member_ids.hourly_rate')
    def _compute_combined_rate(self):
        for crew in self:
            crew.combined_rate = sum(
                crew.billing_member_ids.mapped('hourly_rate')
            )


class CrewMember(models.Model):
    """Crew member with individual billing rate, linked to hr.employee."""
    _name = 'ps.crew.member'
    _description = 'Crew Member'
    _order = 'id'

    crew_id = fields.Many2one(
        'ps.crew', string='Crew',
        required=True, ondelete='cascade',
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Employee',
        required=True,
    )
    hourly_rate = fields.Float(
        string='Rate ($/hr)',
        required=True,
        help='Billing rate for this crew member',
    )
