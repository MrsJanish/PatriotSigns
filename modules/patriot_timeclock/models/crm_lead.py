# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CrmLeadTimeTracking(models.Model):
    """
    Extend CRM Lead with time tracking fields.
    
    This is in patriot_timeclock because it references ps.time.punch.
    """
    _inherit = 'crm.lead'

    # =========================================================================
    # TIME TRACKING (Bidding Time)
    # =========================================================================
    linked_project_id = fields.Many2one(
        'project.project',
        string='Linked Project',
        compute='_compute_linked_project_id',
        help='The project created when this opportunity was won'
    )
    time_punch_ids = fields.One2many(
        'ps.time.punch',
        'opportunity_id',
        string='Time Punches'
    )
    bidding_hours = fields.Float(
        string='Bidding Hours',
        compute='_compute_bidding_hours',
        help='Total hours spent on bidding/estimating this opportunity'
    )
    bidding_hours_display = fields.Char(
        string='Bidding Time',
        compute='_compute_bidding_hours'
    )
    total_project_hours = fields.Float(
        string='Total Project Hours',
        compute='_compute_bidding_hours',
        help='Combined bidding + project work hours (if won)'
    )
    total_project_hours_display = fields.Char(
        string='Total Project Time',
        compute='_compute_bidding_hours'
    )
    
    def _compute_linked_project_id(self):
        """Find the project linked to this opportunity."""
        Project = self.env['project.project']
        for lead in self:
            project = Project.search([('opportunity_id', '=', lead.id)], limit=1)
            lead.linked_project_id = project if project else False
    
    @api.depends('time_punch_ids', 'time_punch_ids.duration_hours')
    def _compute_bidding_hours(self):
        TimePunch = self.env['ps.time.punch']
        for lead in self:
            # Bidding time (logged directly to opportunity)
            opp_punches = lead.time_punch_ids.filtered(lambda p: p.state == 'closed')
            bidding_total = sum(opp_punches.mapped('duration_hours'))
            lead.bidding_hours = bidding_total
            
            # Format bidding time
            hours = int(bidding_total)
            minutes = int((bidding_total - hours) * 60)
            lead.bidding_hours_display = f"{hours}h {minutes}m"
            
            # Combined total (bidding + project work if won)
            project_hours = 0
            if lead.linked_project_id:
                project_punches = TimePunch.search([
                    ('project_id', '=', lead.linked_project_id.id),
                    ('state', '=', 'closed')
                ])
                project_hours = sum(project_punches.mapped('duration_hours'))
            
            total = bidding_total + project_hours
            lead.total_project_hours = total
            
            # Format total time
            hours = int(total)
            minutes = int((total - hours) * 60)
            lead.total_project_hours_display = f"{hours}h {minutes}m"
