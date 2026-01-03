{
    'name': 'Patriot Intro',
    'version': '1.0',
    'summary': 'A beautiful welcome experience for Patriot Signs',
    'description': """
        A stunning client action module that serves as a beautiful landing page/intro 
        for the Patriot Signs Odoo system.
    """,
    'category': 'Productivity',
    'author': 'Patriot Signs',
    'depends': ['base', 'web'],
    'data': [
        'data/company_data.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'patriot_intro/static/src/css/splash.css',
            'patriot_intro/static/src/xml/splash_screen.xml',
            'patriot_intro/static/src/js/splash_screen.js',
        ],
    },
    'installable': False,  # DEPRECATED: Use patriot_signage instead
    'application': False,
    'license': 'LGPL-3',
}
