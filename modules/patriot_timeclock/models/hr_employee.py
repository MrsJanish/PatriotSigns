# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployeeAutoTracking(models.Model):
    """
    Extend hr.employee with auto time tracking settings.
    """
    _inherit = 'hr.employee'

    auto_time_tracking = fields.Boolean(
        string='Auto Time Tracking',
        default=True,
        help='Automatically switch time tracking based on which project/opportunity you view in Odoo'
    )
