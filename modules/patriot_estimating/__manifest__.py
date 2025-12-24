{
    'name': 'Patriot Estimating',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Sign project estimating and quoting',
    'description': """
Patriot Estimating Module
=========================

Estimating and quoting for sign projects:
- Estimate creation from CRM opportunities
- Cost breakdown by sign type
- Labor, material, and installation costing
- Markup and margin calculations
- Quote generation

Links CRM opportunities to detailed cost estimates.
    """,
    'author': 'Patriot Signs',
    'website': 'https://patriotsigns.com',
    'depends': [
        'patriot_signage',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/estimate_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'demo': [
        'demo/demo_estimate.xml',
    ],
}
