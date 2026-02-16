{
    'name': 'Omega Estimating',
    'version': '19.0.1.2.0',
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
- Installation crew integration

Links CRM opportunities to detailed cost estimates.
    """,
    'author': 'Omega Signs Co',
    'website': 'https://omegasignsco.com',
    'depends': [
        'patriot_signage',
        'patriot_field_service',
        'hr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/crew_form_billing.xml',
        'views/estimate_views.xml',
        'views/crm_lead_views.xml',
        'views/waste_dashboard.xml',
        'views/menu.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'patriot_estimating/static/src/js/crm_form_reload.js',
        ],
    },
    'demo': [
        'demo/demo_estimate.xml',
    ],
}
