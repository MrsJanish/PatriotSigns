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
    'data': [
        # 'views/res_users_preferences.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'patriot_theme/static/src/css/backend_theme.css',
            # 'patriot_theme/static/src/css/aurora_theme.css',
            # 'patriot_theme/static/src/js/aurora_canvas.js',
            # 'patriot_theme/static/src/xml/aurora_canvas.xml',
            # 'patriot_theme/static/src/js/theme_service.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
