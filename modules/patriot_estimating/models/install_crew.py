# -*- coding: utf-8 -*-
from odoo import models, fields, api


class InstallCrew(models.Model):
    """Installation crew with named members and billing rates."""
    _name = 'ps.install.crew'
    _description = 'Installation Crew'
    _order = 'name'

    name = fields.Char(string='Crew Name', required=True)
    active = fields.Boolean(default=True)
    member_ids = fields.One2many(
        'ps.install.crew.member', 'crew_id',
        string='Members',
    )
    crew_size = fields.Integer(
        string='Crew Size',
        compute='_compute_crew_totals',
        store=True,
    )
    combined_rate = fields.Float(
        string='Combined Rate ($/hr)',
        compute='_compute_crew_totals',
        store=True,
        help='Sum of all member hourly rates',
    )

    @api.depends('member_ids.hourly_rate')
    def _compute_crew_totals(self):
        for crew in self:
            crew.crew_size = len(crew.member_ids)
            crew.combined_rate = sum(crew.member_ids.mapped('hourly_rate'))


class InstallCrewMember(models.Model):
    """Individual member of an installation crew."""
    _name = 'ps.install.crew.member'
    _description = 'Crew Member'
    _order = 'id'

    crew_id = fields.Many2one(
        'ps.install.crew', string='Crew',
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
