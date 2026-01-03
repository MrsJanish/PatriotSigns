{
    'name': 'Omega Intro',
    'version': '1.0',
    'summary': 'A beautiful welcome experience for Omega Signs Co',
    'description': """
        A stunning client action module that serves as a beautiful landing page/intro 
        for the Omega Signs Co Odoo system.
    """,
    'category': 'Productivity',
    'author': 'Omega Signs Co',
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
    'installable': True,  # Must be True - production has it installed
    'application': False,
    'license': 'LGPL-3',
}
