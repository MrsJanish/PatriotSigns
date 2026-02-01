# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class TimeClockKiosk(models.TransientModel):
    """
    Time Clock Kiosk - Transient model for clock in/out actions.
    
    This is the interface employees use to clock in and out.
    """
    _name = 'ps.time.clock.kiosk'
    _description = 'Time Clock'
    _rec_name = 'display_name'
    
    display_name = fields.Char(
        string='Name',
        compute='_compute_display_name'
    )
    
    @api.depends('employee_id')
    def _compute_display_name(self):
        for rec in self:
            if rec.employee_id:
                rec.display_name = f"Time Clock - {rec.employee_id.name}"
            else:
                rec.display_name = "Time Clock"

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
    current_work_item = fields.Char(
        string='Working On',
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
    
    # Task-based clock-in fields
    recommended_task_id = fields.Many2one(
        'project.task',
        string='Recommended Task',
        compute='_compute_recommended_task',
        help='Your highest priority assigned task'
    )
    assigned_task_ids = fields.Many2many(
        'project.task',
        string='Your Assigned Tasks',
        compute='_compute_recommended_task',
        help='All tasks assigned to you, ordered by priority'
    )
    
    @api.depends('employee_id')
    def _compute_recommended_task(self):
        """Find the highest priority task assigned to the current employee."""
        Task = self.env['project.task']
        for kiosk in self:
            if not kiosk.employee_id or not kiosk.employee_id.user_id:
                kiosk.recommended_task_id = False
                kiosk.assigned_task_ids = False
                continue
            
            user_id = kiosk.employee_id.user_id.id
            
            # Find all tasks assigned to this user, ordered by priority
            # Priority: assigned first, then by priority_sequence (lower = higher priority)
            assigned_tasks = Task.search([
                ('user_ids', 'in', [user_id]),
                ('work_state', 'in', ['assigned', 'in_progress', 'not_started']),
                ('is_closed', '=', False),
            ], order='priority_sequence asc, id desc', limit=20)
            
            kiosk.assigned_task_ids = assigned_tasks
            kiosk.recommended_task_id = assigned_tasks[0] if assigned_tasks else False

    @api.depends('employee_id')
    def _compute_status(self):
        TimePunch = self.env['ps.time.punch']
        for kiosk in self:
            active_punch = TimePunch.get_active_punch(kiosk.employee_id.id)
            kiosk.active_punch_id = active_punch
            kiosk.is_clocked_in = bool(active_punch)
            kiosk.current_project_id = active_punch.project_id if active_punch else False
            kiosk.current_duration = active_punch.duration_display if active_punch else "0h 0m"
            
            # Show project name OR opportunity name
            if active_punch:
                if active_punch.project_id:
                    kiosk.current_work_item = active_punch.project_id.name
                elif active_punch.opportunity_id:
                    kiosk.current_work_item = f"[Bid] {active_punch.opportunity_id.name}"
                else:
                    kiosk.current_work_item = "Unknown"
            else:
                kiosk.current_work_item = ""

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
        Clock in to a task, project, or opportunity.
        
        If already clocked into another item, auto-clock-out from it first.
        This simplifies the UX - employees just select where they're working.
        """
        self.ensure_one()
        
        if not self.employee_id:
            raise UserError(
                "No Employee record found for your user account. "
                "Please ask your administrator to create an Employee record for you."
            )
        
        # Can clock into: recommended_task, specific task, project, or opportunity
        target_task = self.recommended_task_id or self.task_id
        if not target_task and not self.project_id and not self.opportunity_id:
            raise UserError("Please select a task, project, or opportunity to clock into.")
        
        # Determine what we're clocking into
        if target_task:
            work_name = f"{target_task.project_id.name} / {target_task.name}"
        elif self.project_id:
            work_name = self.project_id.name
        else:
            work_name = f"[Bid] {self.opportunity_id.name}"
        
        # If already clocked in to the SAME item, do nothing
        if self.is_clocked_in:
            current = self.active_punch_id
            same_task = target_task and current.task_id == target_task
            same_project = not target_task and self.project_id and current.project_id == self.project_id
            same_opp = self.opportunity_id and current.opportunity_id == self.opportunity_id
            if same_task or same_project or same_opp:
                return self._get_reload_action()
        
        old_work = None
        
        # If clocked into something else, auto-clock-out first
        if self.is_clocked_in:
            old_work = self.active_punch_id.work_item
            self.active_punch_id.action_clock_out()
        
        # Create new punch - prioritize task, then project, then opportunity
        punch_vals = {
            'employee_id': self.employee_id.id,
            'notes': self.notes,
            'state': 'active',
        }
        
        if target_task:
            # Task-based clock-in: set both task and its project
            punch_vals['task_id'] = target_task.id
            punch_vals['project_id'] = target_task.project_id.id
        elif self.project_id:
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
