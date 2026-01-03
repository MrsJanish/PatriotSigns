# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class TimeClockKiosk(models.TransientModel):
    """
    Time Clock Kiosk - Transient model for clock in/out actions.
    
    This is the interface employees use to clock in and out.
    """
    _name = 'ps.time.clock.kiosk'
    _description = 'Time Clock Kiosk'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        default=lambda self: self.env.user.employee_id,
        required=True
    )
    
    # Current status
    is_clocked_in = fields.Boolean(
        string='Currently Clocked In',
        compute='_compute_status'
    )
    active_punch_id = fields.Many2one(
        'ps.time.punch',
        string='Active Punch',
        compute='_compute_status'
    )
    current_project_id = fields.Many2one(
        'project.project',
        string='Current Project',
        compute='_compute_status'
    )
    current_duration = fields.Char(
        string='Time Elapsed',
        compute='_compute_status'
    )
    
    # For clocking in
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        domain=[('active', '=', True)]
    )
    task_id = fields.Many2one(
        'project.task',
        string='Task',
        domain="[('project_id', '=', project_id)]"
    )
    notes = fields.Text(
        string='What are you working on?'
    )

    @api.depends('employee_id')
    def _compute_status(self):
        TimePunch = self.env['ps.time.punch']
        for kiosk in self:
            active_punch = TimePunch.get_active_punch(kiosk.employee_id.id)
            kiosk.active_punch_id = active_punch
            kiosk.is_clocked_in = bool(active_punch)
            kiosk.current_project_id = active_punch.project_id if active_punch else False
            kiosk.current_duration = active_punch.duration_display if active_punch else "0h 0m"

    def action_clock_in(self):
        """Clock in to a project."""
        self.ensure_one()
        
        if not self.project_id:
            raise UserError("Please select a project to clock into.")
        
        # Check if already clocked in
        if self.is_clocked_in:
            raise UserError(
                f"You are already clocked into {self.current_project_id.name}. "
                "Please clock out first or use 'Switch Project'."
            )
        
        # Create new punch
        punch = self.env['ps.time.punch'].create({
            'employee_id': self.employee_id.id,
            'project_id': self.project_id.id,
            'task_id': self.task_id.id if self.task_id else False,
            'notes': self.notes,
            'state': 'active',
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Clocked In!',
                'message': f'You are now clocked into {self.project_id.name}',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_clock_out(self):
        """Clock out from current project."""
        self.ensure_one()
        
        if not self.is_clocked_in:
            raise UserError("You are not currently clocked in.")
        
        # Clock out the active punch
        self.active_punch_id.action_clock_out()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Clocked Out!',
                'message': f'Logged {self.current_duration} to {self.current_project_id.name}',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_switch_project(self):
        """Switch to a different project (clock out current, clock into new)."""
        self.ensure_one()
        
        if not self.project_id:
            raise UserError("Please select a project to switch to.")
        
        if self.project_id == self.current_project_id:
            raise UserError("You're already working on this project.")
        
        old_project = self.current_project_id.name if self.current_project_id else "None"
        
        # Clock out current if clocked in
        if self.is_clocked_in:
            self.active_punch_id.action_clock_out()
        
        # Clock into new project
        self.env['ps.time.punch'].create({
            'employee_id': self.employee_id.id,
            'project_id': self.project_id.id,
            'task_id': self.task_id.id if self.task_id else False,
            'notes': self.notes,
            'state': 'active',
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Switched Project!',
                'message': f'Switched from {old_project} to {self.project_id.name}',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_open_kiosk(self):
        """Open the kiosk in a new window."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Time Clock',
            'res_model': 'ps.time.clock.kiosk',
            'view_mode': 'form',
            'target': 'new',
            'context': {'form_view_initial_mode': 'edit'},
        }
