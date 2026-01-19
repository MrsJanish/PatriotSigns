# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class TimePunch(models.Model):
    """
    Time Punch - Records clock in/out for employee time tracking.
    
    Employees cannot edit these directly - only clock in/out buttons work.
    Admins can adjust times for missed punches.
    """
    _name = 'ps.time.punch'
    _description = 'Time Punch'
    _inherit = ['mail.thread']
    _order = 'punch_in desc'

    # Employee
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True,
        default=lambda self: self.env.user.employee_id
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        related='employee_id.user_id',
        store=True
    )
    
    # Project/Task (for won projects)
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        tracking=True
    )
    task_id = fields.Many2one(
        'project.task',
        string='Task',
        domain="[('project_id', '=', project_id)]"
    )
    
    # Opportunity (for pre-bid time - before project exists)
    opportunity_id = fields.Many2one(
        'crm.lead',
        string='Opportunity',
        tracking=True,
        help='For logging time to opportunities before they become projects'
    )
    
    # Computed: What we're working on (project or opportunity name)
    work_item = fields.Char(
        string='Work Item',
        compute='_compute_work_item',
        store=True
    )
    
    @api.depends('project_id', 'opportunity_id')
    def _compute_work_item(self):
        for punch in self:
            if punch.project_id:
                punch.work_item = punch.project_id.name
            elif punch.opportunity_id:
                punch.work_item = f"[Bid] {punch.opportunity_id.name}"
            else:
                punch.work_item = "Unknown"
    
    # Time tracking
    punch_in = fields.Datetime(
        string='Clock In',
        required=True,
        tracking=True,
        default=fields.Datetime.now
    )
    punch_out = fields.Datetime(
        string='Clock Out',
        tracking=True
    )
    
    # Computed duration
    duration_hours = fields.Float(
        string='Duration (Hours)',
        compute='_compute_duration_hours',
        store=True
    )
    duration_display = fields.Char(
        string='Duration',
        compute='_compute_duration_display'
    )
    
    # State
    state = fields.Selection([
        ('active', 'Clocked In'),
        ('closed', 'Clocked Out'),
    ], string='Status', default='active', tracking=True)
    
    # Notes
    notes = fields.Text(
        string='Notes',
        help='What are you working on?'
    )
    
    # Adjustment tracking
    adjusted_by = fields.Many2one(
        'res.users',
        string='Adjusted By',
        readonly=True
    )
    adjustment_reason = fields.Text(
        string='Adjustment Reason',
        readonly=True
    )
    
    # Link to timesheet (for integration)
    timesheet_id = fields.Many2one(
        'account.analytic.line',
        string='Timesheet Entry',
        readonly=True
    )

    @api.depends('punch_in', 'punch_out')
    def _compute_duration_hours(self):
        """Compute stored duration in hours."""
        for punch in self:
            if punch.punch_in:
                end_time = punch.punch_out or fields.Datetime.now()
                delta = end_time - punch.punch_in
                punch.duration_hours = delta.total_seconds() / 3600.0
            else:
                punch.duration_hours = 0.0

    @api.depends('punch_in', 'punch_out')
    def _compute_duration_display(self):
        """Compute non-stored display duration."""
        for punch in self:
            if punch.punch_in:
                end_time = punch.punch_out or fields.Datetime.now()
                delta = end_time - punch.punch_in
                total_hours = delta.total_seconds() / 3600.0
                hours = int(total_hours)
                minutes = int((total_hours - hours) * 60)
                punch.duration_display = f"{hours}h {minutes}m"
            else:
                punch.duration_display = "0h 0m"

    def action_clock_out(self):
        """Clock out - sets punch_out to now and creates timesheet entry."""
        self.ensure_one()
        
        if self.state == 'closed':
            raise UserError("Already clocked out!")
        
        self.write({
            'punch_out': fields.Datetime.now(),
            'state': 'closed',
        })
        
        # Create timesheet entry
        self._create_timesheet_entry()
        
        return True
    
    def _create_timesheet_entry(self):
        """Create an account.analytic.line (timesheet) entry from this punch."""
        self.ensure_one()
        
        if not self.punch_out:
            return
        
        # Find or create analytic account for the project
        analytic_line = self.env['account.analytic.line'].sudo().create({
            'name': self.notes or f"Time punch: {self.project_id.name}",
            'project_id': self.project_id.id,
            'task_id': self.task_id.id if self.task_id else False,
            'employee_id': self.employee_id.id,
            'unit_amount': self.duration_hours,
            'date': self.punch_in.date(),
        })
        
        self.timesheet_id = analytic_line.id
    
    @api.model
    def get_active_punch(self, employee_id=None):
        """Get the currently active punch for an employee."""
        if not employee_id:
            employee_id = self.env.user.employee_id.id
        
        return self.search([
            ('employee_id', '=', employee_id),
            ('state', '=', 'active'),
        ], limit=1)
    
    def action_admin_adjust(self, punch_in=None, punch_out=None, reason=None):
        """Admin adjustment of punch times."""
        self.ensure_one()
        
        if not self.env.user.has_group('base.group_system'):
            raise UserError("Only administrators can adjust time punches.")
        
        vals = {
            'adjusted_by': self.env.user.id,
            'adjustment_reason': reason or "Manual adjustment",
        }
        
        if punch_in:
            vals['punch_in'] = punch_in
        if punch_out:
            vals['punch_out'] = punch_out
            vals['state'] = 'closed'
        
        self.write(vals)
        
        # Recreate timesheet if needed
        if self.timesheet_id and punch_out:
            self.timesheet_id.unlink()
            self._create_timesheet_entry()
        
        return True

    @api.model
    def auto_switch_to_record(self, model, record_id):
        """
        Automatically switch time tracking to the specified record.
        Called by JS activity tracker when user views a project/opportunity.
        
        :param model: 'project.project' or 'crm.lead'
        :param record_id: ID of the record being viewed
        :return: dict with result info
        """
        employee = self.env.user.employee_id
        if not employee:
            return {'success': False, 'error': 'No employee record'}
        
        # Check if auto-tracking is enabled for this employee
        if not employee.auto_time_tracking:
            return {'success': False, 'error': 'Auto tracking disabled'}
        
        # Determine project/opportunity from the viewed record
        project_id = False
        opportunity_id = False
        
        if model == 'project.project':
            project_id = record_id
        elif model == 'crm.lead':
            opportunity_id = record_id
        else:
            return {'success': False, 'error': f'Unsupported model: {model}'}
        
        # Get current active punch
        active_punch = self.get_active_punch(employee.id)
        
        # Check if already on this record
        if active_punch:
            if project_id and active_punch.project_id.id == project_id:
                return {'success': True, 'action': 'already_on_record'}
            if opportunity_id and active_punch.opportunity_id.id == opportunity_id:
                return {'success': True, 'action': 'already_on_record'}
            
            # Clock out from current
            active_punch.action_clock_out()
        
        # Clock in to new record
        new_punch = self.create({
            'employee_id': employee.id,
            'project_id': project_id,
            'opportunity_id': opportunity_id,
            'notes': '[Auto-tracked]',
            'state': 'active',
        })
        
        return {
            'success': True,
            'action': 'switched' if active_punch else 'started',
            'punch_id': new_punch.id,
        }


class TimePunchAdjustmentWizard(models.TransientModel):
    """Wizard for admins to adjust time punches."""
    _name = 'ps.time.punch.adjustment.wizard'
    _description = 'Time Punch Adjustment'

    punch_id = fields.Many2one(
        'ps.time.punch',
        string='Time Punch',
        required=True
    )
    new_punch_in = fields.Datetime(
        string='New Clock In Time'
    )
    new_punch_out = fields.Datetime(
        string='New Clock Out Time'
    )
    reason = fields.Text(
        string='Reason for Adjustment',
        required=True
    )

    def action_apply_adjustment(self):
        """Apply the adjustment to the time punch."""
        self.ensure_one()
        self.punch_id.action_admin_adjust(
            punch_in=self.new_punch_in,
            punch_out=self.new_punch_out,
            reason=self.reason
        )
        return {'type': 'ir.actions.act_window_close'}
