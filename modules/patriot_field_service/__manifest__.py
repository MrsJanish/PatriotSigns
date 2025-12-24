{
    'name': 'Patriot Field Service',
    'version': '19.0.1.0.0',
    'category': 'Field Service',
    'summary': 'Sign installation and field service',
    'description': """
Patriot Field Service Module
============================

Installation and field service management:
- Installation scheduling and crew assignment
- Site visit planning
- Punchlist tracking
- Installation photos and documentation
- Time tracking for installations

Manages all field activities after signs leave the shop.
    """,
    'author': 'Patriot Signs',
    'website': 'https://patriotsigns.com',
    'depends': [
        'patriot_production',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/default_crew.xml',
        'views/installation_views.xml',
        'views/crew_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
