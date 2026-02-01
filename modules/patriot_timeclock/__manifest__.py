{
    'name': 'Omega Time Clock',
    'version': '19.0.2.0.0',
    'category': 'Human Resources',
    'summary': 'Clock in/out time tracking with work assignment',
    'description': """
Omega Time Clock Module v2.0
=============================

Button-based time tracking for employees:
- Clock in/out to projects and tasks
- **NEW** My Work Dashboard (/my-work) for quick task switching
- **NEW** Production phases (Design, Fab, Sand, Pack, etc.)
- **NEW** Manager work assignment board
- **NEW** QR code scanning for task switching
- Internal projects for non-billable work
- Kiosk mode for shop floor
- Admin-only time adjustments

Employees see their assigned tasks in a mobile-friendly dashboard.
Managers assign work via drag-and-drop kanban.
    """,
    'author': 'Omega Signs Co',
    'website': 'https://omegasignsco.com',
    'depends': [
        'hr',
        'project',
        'hr_timesheet',
        'patriot_projects',
        'website',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'data/internal_projects.xml',
        'data/production_phases.xml',
        'views/menu.xml',  
        'views/time_punch_views.xml',
        'views/time_clock_kiosk_views.xml',
        'views/barcode_kiosk_views.xml',
        'views/production_phase_views.xml',
        'views/work_assignment_views.xml',
        'views/my_work_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'patriot_timeclock/static/src/css/time_clock.css',
            'patriot_timeclock/static/src/css/barcode_kiosk.css',
            'patriot_timeclock/static/src/js/time_clock_kiosk.js',
            'patriot_timeclock/static/src/js/barcode_kiosk.js',
            'patriot_timeclock/static/src/xml/time_clock_kiosk.xml',
        ],
        'web.assets_frontend': [
            'patriot_timeclock/static/src/css/my_work.css',
            'patriot_timeclock/static/src/js/my_work.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
