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
    
    # For clocking in - can choose project OR opportunity
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        domain=[('active', '=', True)]
    )
    opportunity_id = fields.Many2one(
        'crm.lead',
        string='Opportunity',
        domain=[('type', '=', 'opportunity')],
        help='Select an opportunity for pre-bid work'
    )
    task_id = fields.Many2one(
        'project.task',
        string='Task',
        domain="[('project_id', '=', project_id)]"
    )
    notes = fields.Text(
        string='Notes'
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
        
        # Must select either project or opportunity
        if not self.project_id and not self.opportunity_id:
            raise UserError("Please select a project or opportunity to clock into.")
        
        # Determine what we're clocking into
        work_name = self.project_id.name if self.project_id else f"[Bid] {self.opportunity_id.name}"
        
        # If already clocked in to the SAME item, do nothing
        if self.is_clocked_in:
            current = self.active_punch_id
            same_project = self.project_id and current.project_id == self.project_id
            same_opp = self.opportunity_id and current.opportunity_id == self.opportunity_id
            if same_project or same_opp:
                return self._get_reload_action()
        
        old_work = None
        
        # If clocked into something else, auto-clock-out first
        if self.is_clocked_in:
            old_work = self.active_punch_id.work_item
            self.active_punch_id.action_clock_out()
        
        # Create new punch - can have project OR opportunity (not both)
        punch_vals = {
            'employee_id': self.employee_id.id,
            'notes': self.notes,
            'state': 'active',
        }
        
        if self.project_id:
            punch_vals['project_id'] = self.project_id.id
            punch_vals['task_id'] = self.task_id.id if self.task_id else False
        else:
            punch_vals['opportunity_id'] = self.opportunity_id.id
        
        self.env['ps.time.punch'].create(punch_vals)
        
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
