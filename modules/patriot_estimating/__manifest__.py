{
    'name': 'Omega Estimating',
    'version': '19.0.1.1.0',
    'category': 'Sales',
    'summary': 'Sign project estimating and quoting',
    'description': """
Omega Estimating Module
=========================

Estimating and quoting for sign projects:
- Estimate creation from CRM opportunities
- Cost breakdown by sign type
- Labor, material, and installation costing
- Markup and margin calculations
- Quote generation
- Installation crew management

Links CRM opportunities to detailed cost estimates.
    """,
    'author': 'Omega Signs Co',
    'website': 'https://omegasignsco.com',
    'depends': [
        'patriot_signage',
        'hr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'data/install_crews.xml',
        'views/install_crew_views.xml',
        'views/estimate_views.xml',
        'views/waste_dashboard.xml',
        'views/menu.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'post_init_hook': '_populate_crew_members',
    'demo': [
        'demo/demo_estimate.xml',
    ],
}
