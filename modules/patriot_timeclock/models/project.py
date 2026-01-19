# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProjectTimeTracking(models.Model):
    """
    Extend project.project with time tracking fields.
    
    This is in patriot_timeclock because it references ps.time.punch.
    """
    _inherit = 'project.project'

    # =========================================================================
    # TIME TRACKING
    # =========================================================================
    total_hours = fields.Float(
        string='Total Hours',
        compute='_compute_total_hours'
    )
    total_hours_display = fields.Char(
        string='Total Time',
        compute='_compute_total_hours'
    )
    time_punch_ids = fields.One2many(
        'ps.time.punch',
        'project_id',
        string='Time Punches'
    )
    time_punch_count = fields.Integer(
        string='Punch Count',
        compute='_compute_total_hours'
    )
    
    # Barcode for kiosk time tracking
    project_barcode = fields.Char(
        string='Time Clock Barcode',
        copy=False,
        help='Barcode for scanning at time clock kiosks'
    )
    
    @api.depends('time_punch_ids', 'time_punch_ids.duration_hours', 'opportunity_id')
    def _compute_total_hours(self):
        TimePunch = self.env['ps.time.punch']
        for project in self:
            # Project punches
            project_punches = project.time_punch_ids.filtered(lambda p: p.state == 'closed')
            project_hours = sum(project_punches.mapped('duration_hours'))
            
            # Also include opportunity punches (pre-bid time) if linked
            opp_hours = 0
            if project.opportunity_id:
                opp_punches = TimePunch.search([
                    ('opportunity_id', '=', project.opportunity_id.id),
                    ('state', '=', 'closed')
                ])
                opp_hours = sum(opp_punches.mapped('duration_hours'))
            
            total = project_hours + opp_hours
            project.total_hours = total
            project.time_punch_count = len(project.time_punch_ids)
            
            # Format as Xh Ym
            hours = int(total)
            minutes = int((total - hours) * 60)
            project.total_hours_display = f"{hours}h {minutes}m"
