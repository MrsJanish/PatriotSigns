{
    'name': 'Omega Time Clock',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Clock in/out time tracking for employees',
    'description': """
Omega Time Clock Module
=========================

Button-based time tracking for employees:
- Clock in/out to projects (no manual time entry)
- Internal projects for non-billable work
- Kiosk mode for shop floor
- Admin-only time adjustments

Employees click to start/stop tracking, cannot manually enter hours.
    """,
    'author': 'Omega Signs Co',
    'website': 'https://omegasignsco.com',
    'depends': [
        'hr',
        'project',
        'hr_timesheet',
        'patriot_projects',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'data/internal_projects.xml',
        'views/menu.xml',  # Must load first - defines menu_timeclock_app
        'views/time_punch_views.xml',
        'views/time_clock_kiosk_views.xml',
        'views/barcode_kiosk_views.xml',
        # 'views/hr_employee_views.xml',  # Temporarily disabled - needs upgrade first
    ],
    'assets': {
        'web.assets_backend': [
            'patriot_timeclock/static/src/css/time_clock.css',
            'patriot_timeclock/static/src/css/barcode_kiosk.css',
            'patriot_timeclock/static/src/js/time_clock_kiosk.js',
            'patriot_timeclock/static/src/js/barcode_kiosk.js',
            # 'patriot_timeclock/static/src/js/auto_time_tracker.js',  # Disabled until upgrade
            'patriot_timeclock/static/src/xml/time_clock_kiosk.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
