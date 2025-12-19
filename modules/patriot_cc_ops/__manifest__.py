{
    'name': 'Construct Connect Opportunities',
    'version': '19.0.1.0.0',
    'summary': 'Automate ITB ingestion from ConstructConnect emails',
    'description': """
        This module monitors incoming emails for ConstructConnect ITB notifications,
        fetches project details via API, and stores construction documents.
    """,
    'category': 'Sales/CRM',
    'author': 'Patriot Signs',
    'depends': ['mail', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/cc_opportunity_views.xml',
        'views/menus.xml',
        'data/ir_config_parameter.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'patriot_cc_ops/static/src/css/cc_ops.css',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
