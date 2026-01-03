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
        default=lambda self: self._get_current_employee()
    )

    @api.model
    def _get_current_employee(self):
        """Get current employee, with helpful error if not found."""
        employee = self.env.user.employee_id
        return employee.id if employee else False
    
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

    def _get_reload_action(self):
        """Return action to reload the time clock kiosk."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Clock In / Out',
            'res_model': 'ps.time.clock.kiosk',
            'view_mode': 'form',
            'target': 'current',
            'context': {'form_view_initial_mode': 'edit'},
        }

    def action_clock_in(self):
        """
        Clock in to a project.
        
        If already clocked into another project, auto-clock-out from it first.
        This simplifies the UX - employees just select where they're working.
        """
        self.ensure_one()
        
        if not self.employee_id:
            raise UserError(
                "No Employee record found for your user account. "
                "Please ask your administrator to create an Employee record for you."
            )
        
        if not self.project_id:
            raise UserError("Please select a project to clock into.")
        
        # If already clocked in to the SAME project, do nothing
        if self.is_clocked_in and self.project_id == self.current_project_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Already Working',
                    'message': f'You are already clocked into {self.project_id.name}',
                    'type': 'info',
                    'sticky': False,
                }
            }
        
        old_project = None
        
        # If clocked into a DIFFERENT project, auto-clock-out first
        if self.is_clocked_in:
            old_project = self.current_project_id.name
            self.active_punch_id.action_clock_out()
        
        # Create new punch
        self.env['ps.time.punch'].create({
            'employee_id': self.employee_id.id,
            'project_id': self.project_id.id,
            'task_id': self.task_id.id if self.task_id else False,
            'notes': self.notes,
            'state': 'active',
        })
        
        if old_project:
            message = f'Switched from {old_project} to {self.project_id.name}'
            title = 'Switched Project!'
        else:
            message = f'You are now clocked into {self.project_id.name}'
            title = 'Clocked In!'
        
        # Reload the form to show updated status
        return self._get_reload_action()

    def action_clock_out(self):
        """Clock out from current project (end of day/session)."""
        self.ensure_one()
        
        if not self.is_clocked_in:
            raise UserError("You are not currently clocked in.")
        
        project_name = self.current_project_id.name
        duration = self.current_duration
        
        # Clock out the active punch
        self.active_punch_id.action_clock_out()
        
        # Reload the form to show updated status
        return self._get_reload_action()

    def action_take_break(self):
        """
        Take a break - clocks out current project, clocks into Break project.
        
        Uses the internal 'Break' project created during module install.
        """
        self.ensure_one()
        
        # Find the Break project
        break_project = self.env.ref('patriot_timeclock.project_break', raise_if_not_found=False)
        
        if not break_project:
            # Fallback: search for it by name
            break_project = self.env['project.project'].search([('name', '=', 'Break')], limit=1)
        
        if not break_project:
            raise UserError("Break project not found. Please contact your administrator.")
        
        old_project = None
        
        # Clock out of current project if clocked in
        if self.is_clocked_in:
            old_project = self.current_project_id.name
            self.active_punch_id.action_clock_out()
        
        # Clock into Break project
        self.env['ps.time.punch'].create({
            'employee_id': self.employee_id.id,
            'project_id': break_project.id,
            'notes': 'Break',
            'state': 'active',
        })
        
        # Reload the form to show updated status
        return self._get_reload_action()

    def action_end_break(self):
        """
        End break - clocks out of Break project.
        
        Employee should then clock into their next project.
        """
        self.ensure_one()
        
        if not self.is_clocked_in:
            raise UserError("You are not on a break.")
        
        # Verify they're on break
        if self.current_project_id.name != 'Break':
            raise UserError("You're not currently on break.")
        
        self.active_punch_id.action_clock_out()
        
        # Reload the form to show updated status
        return self._get_reload_action()

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
