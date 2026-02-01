# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import qrcode
import base64
from io import BytesIO


class ProjectTaskExtension(models.Model):
    """
    Extend project.task with production phase, work assignment, and status tracking.
    
    This enables:
    - Categorizing tasks by production phase (Fab, Sand, Pack, etc.)
    - Assigning tasks to specific employees
    - Quick task switching from the My Work dashboard
    - Tracking work state from assignment to completion
    """
    _inherit = 'project.task'

    # =========================================================================
    # PRODUCTION PHASE
    # =========================================================================
    phase_id = fields.Many2one(
        'ps.production.phase',
        string='Production Phase',
        help='The manufacturing phase this task belongs to'
    )
    phase_sequence = fields.Integer(
        related='phase_id.sequence',
        store=True,
        string='Phase Order'
    )

    # =========================================================================
    # WORK ASSIGNMENT
    # =========================================================================
    assigned_user_ids = fields.Many2many(
        'res.users',
        'project_task_assigned_users_rel',
        'task_id',
        'user_id',
        string='Assigned Workers',
        help='Employees who can work on this task'
    )
    priority_sequence = fields.Integer(
        string='Priority',
        default=10,
        help='Lower numbers appear first in employee work queue'
    )
    assigned_by = fields.Many2one(
        'res.users',
        string='Assigned By',
        readonly=True
    )
    assigned_date = fields.Datetime(
        string='Assigned Date',
        readonly=True
    )

    # =========================================================================
    # WORK STATE
    # =========================================================================
    work_state = fields.Selection([
        ('not_started', 'Not Started'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('complete', 'Complete'),
        ('verified', 'Verified'),
    ], string='Work Status', default='not_started', tracking=True)
    
    # Verification
    is_verified = fields.Boolean(
        string='Verified',
        default=False,
        readonly=True
    )
    verified_by = fields.Many2one(
        'res.users',
        string='Verified By',
        readonly=True
    )
    verified_date = fields.Datetime(
        string='Verified Date',
        readonly=True
    )

    # =========================================================================
    # TIME TRACKING
    # =========================================================================
    actual_hours = fields.Float(
        string='Actual Hours',
        compute='_compute_actual_hours',
        store=True,
        help='Total hours logged via time punches'
    )
    active_punch_id = fields.Many2one(
        'ps.time.punch',
        string='Active Punch',
        compute='_compute_active_punch',
        help='Currently active time punch on this task'
    )
    is_currently_worked = fields.Boolean(
        string='Being Worked',
        compute='_compute_active_punch',
        help='True if someone is currently clocked into this task'
    )
    current_worker_id = fields.Many2one(
        'res.users',
        string='Current Worker',
        compute='_compute_active_punch',
        help='User currently working on this task'
    )

    # =========================================================================
    # QR CODE
    # =========================================================================
    qr_code_image = fields.Binary(
        string='QR Code',
        compute='_compute_qr_code',
        help='QR code for scanning to switch to this task'
    )
    task_barcode = fields.Char(
        string='Task Barcode',
        compute='_compute_task_barcode',
        store=True,
        help='Unique barcode identifier for this task'
    )

    # =========================================================================
    # COMPUTED METHODS
    # =========================================================================

    @api.depends('timesheet_ids', 'timesheet_ids.unit_amount')
    def _compute_actual_hours(self):
        """Sum of all timesheet entries for this task."""
        for task in self:
            task.actual_hours = sum(task.timesheet_ids.mapped('unit_amount'))

    def _compute_active_punch(self):
        """Find if there's an active punch on this task."""
        TimePunch = self.env['ps.time.punch']
        for task in self:
            active = TimePunch.search([
                ('task_id', '=', task.id),
                ('state', '=', 'active'),
            ], limit=1)
            task.active_punch_id = active.id if active else False
            task.is_currently_worked = bool(active)
            task.current_worker_id = active.user_id.id if active else False

    @api.depends('project_id')
    def _compute_task_barcode(self):
        """Generate a unique barcode for the task."""
        for task in self:
            if task.id and task.project_id:
                task.task_barcode = f"TASK-{task.project_id.id}-{task.id}"
            else:
                task.task_barcode = False

    def _compute_qr_code(self):
        """Generate QR code image containing the task barcode."""
        for task in self:
            if task.task_barcode:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(task.task_barcode)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                task.qr_code_image = base64.b64encode(buffer.getvalue())
            else:
                task.qr_code_image = False

    # =========================================================================
    # ASSIGNMENT METHODS
    # =========================================================================

    def action_assign_to_user(self, user_id):
        """Assign this task to a user (manager action)."""
        self.ensure_one()
        user = self.env['res.users'].browse(user_id)
        
        self.write({
            'assigned_user_ids': [(4, user_id)],
            'assigned_by': self.env.user.id,
            'assigned_date': fields.Datetime.now(),
            'work_state': 'assigned' if self.work_state == 'not_started' else self.work_state,
        })
        
        return True

    def action_unassign_user(self, user_id):
        """Remove a user from this task's assignment."""
        self.ensure_one()
        self.write({
            'assigned_user_ids': [(3, user_id)],
        })
        # If no one left assigned, revert to not_started
        if not self.assigned_user_ids and self.work_state == 'assigned':
            self.work_state = 'not_started'
        return True

    # =========================================================================
    # WORK ACTIONS
    # =========================================================================

    def action_start_work(self):
        """
        Employee starts working on this task.
        - Clocks out of any current task
        - Clocks into this task
        - Updates work_state to in_progress
        """
        self.ensure_one()
        employee = self.env.user.employee_id
        
        if not employee:
            raise UserError("No employee record linked to your user account.")
        
        # Check if assigned
        if self.assigned_user_ids and self.env.user not in self.assigned_user_ids:
            raise UserError("You are not assigned to this task.")
        
        TimePunch = self.env['ps.time.punch']
        
        # Clock out of any current active punch
        active_punch = TimePunch.get_active_punch(employee.id)
        if active_punch:
            active_punch.action_clock_out()
        
        # Clock into this task
        new_punch = TimePunch.create({
            'employee_id': employee.id,
            'project_id': self.project_id.id,
            'task_id': self.id,
            'notes': f'Started: {self.name}',
            'state': 'active',
        })
        
        # Update work state
        if self.work_state in ('not_started', 'assigned'):
            self.work_state = 'in_progress'
        
        return {
            'success': True,
            'punch_id': new_punch.id,
            'task_name': self.name,
            'project_name': self.project_id.name,
        }

    def action_switch_to_task(self):
        """
        Quick switch to this task from another task.
        Same as action_start_work but returns to My Work dashboard.
        """
        result = self.action_start_work()
        return {
            'type': 'ir.actions.act_url',
            'url': '/my-work',
            'target': 'self',
        }

    def action_mark_complete(self):
        """
        Employee marks task as complete.
        - Clocks out if currently clocked in
        - Sets work_state to 'complete'
        """
        self.ensure_one()
        employee = self.env.user.employee_id
        
        if employee:
            TimePunch = self.env['ps.time.punch']
            active_punch = TimePunch.search([
                ('task_id', '=', self.id),
                ('employee_id', '=', employee.id),
                ('state', '=', 'active'),
            ], limit=1)
            
            if active_punch:
                active_punch.action_clock_out()
        
        self.work_state = 'complete'
        
        return True

    def action_verify(self):
        """
        Manager verifies a completed task.
        """
        self.ensure_one()
        
        if self.work_state != 'complete':
            raise UserError("Can only verify completed tasks.")
        
        self.write({
            'work_state': 'verified',
            'is_verified': True,
            'verified_by': self.env.user.id,
            'verified_date': fields.Datetime.now(),
        })
        
        return True

    # =========================================================================
    # MY WORK QUEUE
    # =========================================================================

    @api.model
    def get_my_work_queue(self):
        """
        Get tasks assigned to the current user, ordered by priority.
        Returns tasks for the My Work dashboard.
        """
        user = self.env.user
        employee = user.employee_id
        
        if not employee:
            return []
        
        # Find tasks where user is assigned and not yet complete/verified
        domain = [
            ('assigned_user_ids', 'in', [user.id]),
            ('work_state', 'in', ['assigned', 'in_progress']),
        ]
        
        tasks = self.search(domain, order='priority_sequence, id')
        
        # Also find the currently active task (even if not in assigned list)
        TimePunch = self.env['ps.time.punch']
        active_punch = TimePunch.get_active_punch(employee.id)
        active_task_id = active_punch.task_id.id if active_punch and active_punch.task_id else False
        
        result = []
        for task in tasks:
            result.append({
                'id': task.id,
                'name': task.name,
                'project_name': task.project_id.name,
                'phase_name': task.phase_id.name if task.phase_id else '',
                'phase_color': task.phase_id.color if task.phase_id else 0,
                'work_state': task.work_state,
                'is_active': task.id == active_task_id,
                'priority': task.priority_sequence,
                'estimated_hours': task.allocated_hours,
                'actual_hours': task.actual_hours,
            })
        
        return result

    @api.model
    def get_active_task_info(self):
        """
        Get info about the currently active task for the current user.
        """
        employee = self.env.user.employee_id
        if not employee:
            return None
        
        TimePunch = self.env['ps.time.punch']
        active_punch = TimePunch.get_active_punch(employee.id)
        
        if not active_punch:
            return None
        
        task = active_punch.task_id
        
        return {
            'punch_id': active_punch.id,
            'task_id': task.id if task else None,
            'task_name': task.name if task else 'No Task',
            'project_name': active_punch.project_id.name if active_punch.project_id else '',
            'phase_name': task.phase_id.name if task and task.phase_id else '',
            'punch_in': active_punch.punch_in.isoformat() if active_punch.punch_in else None,
            'duration_display': active_punch.duration_display,
            'duration_hours': active_punch.duration_hours,
        }

    @api.model
    def scan_task_barcode(self, barcode):
        """
        Handle QR code scan from My Work dashboard.
        Returns task info or switches to the task.
        """
        task = self.search([('task_barcode', '=', barcode)], limit=1)
        
        if not task:
            return {
                'success': False,
                'error': 'task_not_found',
                'message': f'No task found with barcode: {barcode}'
            }
        
        # Switch to this task
        result = task.action_start_work()
        
        return {
            'success': True,
            'action': 'switched',
            'task_id': task.id,
            'task_name': task.name,
            'project_name': task.project_id.name,
        }
