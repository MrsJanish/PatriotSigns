{
    'name': 'Patriot Design System',
    'version': '1.0',
    'summary': 'Global backend theme for Patriot Signs',
    'description': """
        A centralized design system for Odoo 19.
        - Deep Navy / Soft White Palette
        - Rounded Rectangular Buttons
        - Enhanced Typography (Bolder, clearer)
        - Ergonomic Inputs and Forms
    """,
    'category': 'Theme/Backend',
    'author': 'Patriot Signs',
    'depends': ['web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'patriot_theme/static/src/css/backend_theme.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
