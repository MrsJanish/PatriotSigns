# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json


class MyWorkController(http.Controller):
    """
    Controller for the "My Work" employee dashboard.
    
    Provides a responsive web interface for:
    - Viewing assigned tasks
    - Quick task switching
    - Clocking in/out
    - Marking tasks complete
    - QR code scanning
    """

    @http.route('/my-work', type='http', auth='user', website=True)
    def my_work_dashboard(self, **kwargs):
        """
        Render the My Work dashboard for the current employee.
        """
        user = request.env.user
        employee = user.employee_id
        
        if not employee:
            return request.render('patriot_timeclock.my_work_no_employee', {})
        
        # Get active task info
        Task = request.env['project.task']
        active_info = Task.get_active_task_info()
        
        # Get work queue
        work_queue = Task.get_my_work_queue()
        
        # Get available phases for filtering
        phases = request.env['ps.production.phase'].search([('active', '=', True)])
        
        values = {
            'employee': employee,
            'active_task': active_info,
            'work_queue': work_queue,
            'phases': phases,
            'is_clocked_in': bool(active_info),
        }
        
        return request.render('patriot_timeclock.my_work_dashboard', values)

    @http.route('/my-work/switch-task/<int:task_id>', type='json', auth='user')
    def switch_task(self, task_id, **kwargs):
        """
        AJAX endpoint to switch to a different task.
        Clocks out of current task and clocks into the new one.
        """
        Task = request.env['project.task'].browse(task_id)
        
        if not Task.exists():
            return {'success': False, 'error': 'Task not found'}
        
        try:
            result = Task.action_start_work()
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/my-work/clock-out', type='json', auth='user')
    def clock_out(self, **kwargs):
        """
        AJAX endpoint to clock out completely.
        """
        employee = request.env.user.employee_id
        
        if not employee:
            return {'success': False, 'error': 'No employee record'}
        
        TimePunch = request.env['ps.time.punch']
        active_punch = TimePunch.get_active_punch(employee.id)
        
        if not active_punch:
            return {'success': False, 'error': 'Not clocked in'}
        
        try:
            active_punch.action_clock_out()
            return {'success': True, 'action': 'clocked_out'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/my-work/mark-complete/<int:task_id>', type='json', auth='user')
    def mark_complete(self, task_id, **kwargs):
        """
        AJAX endpoint to mark a task as complete.
        """
        Task = request.env['project.task'].browse(task_id)
        
        if not Task.exists():
            return {'success': False, 'error': 'Task not found'}
        
        try:
            Task.action_mark_complete()
            return {'success': True, 'action': 'completed', 'task_name': Task.name}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/my-work/scan-qr', type='json', auth='user')
    def scan_qr(self, barcode, **kwargs):
        """
        AJAX endpoint to handle QR code scan.
        Looks up the task by barcode and switches to it.
        """
        Task = request.env['project.task']
        
        try:
            result = Task.scan_task_barcode(barcode)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/my-work/get-status', type='json', auth='user')
    def get_status(self, **kwargs):
        """
        AJAX endpoint to get current status (for real-time updates).
        """
        Task = request.env['project.task']
        
        active_info = Task.get_active_task_info()
        work_queue = Task.get_my_work_queue()
        
        return {
            'success': True,
            'active_task': active_info,
            'work_queue': work_queue,
            'is_clocked_in': bool(active_info),
        }
