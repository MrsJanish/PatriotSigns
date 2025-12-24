{
    'name': 'Patriot Signage',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Core sign type and instance management',
    'description': """
Patriot Signage Module
======================

Core sign management functionality:
- Project-scoped sign types (ps.sign.type)
- Individual sign instances (ps.sign.instance)
- Location hierarchy (ps.location)
- PDF bookmarks (ps.sign.bookmark)

This module provides the data structure for tracking signs from 
bid intake through production and installation.
    """,
    'author': 'Patriot Signs',
    'website': 'https://patriotsigns.com',
    'depends': [
        'patriot_base',
        'patriot_crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sign_type_templates.xml',
        'data/mock_sign_types.xml',
        'views/sign_type_views.xml',
        'views/sign_instance_views.xml',
        'views/location_views.xml',
        'views/crm_lead_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'demo': [
        'demo/demo_sign_types.xml',
    ],
}
