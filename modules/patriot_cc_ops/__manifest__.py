{
    'name': 'Construct Connect Opportunities',
    'version': '19.0.2.0.0',
    'summary': 'Automate ITB ingestion from ConstructConnect with beautiful dashboard',
    'description': """
        This module monitors incoming emails for ConstructConnect ITB notifications,
        fetches project details via API, and stores construction documents.
        
        Features a beautiful glassmorphism dashboard with:
        - Expandable project cards
        - Two theme options (Splash & Aurora Borealis)
        - Per-user theme preference persistence
        - Search by project, contact, or location
        - Integrated document viewer
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
            # CSS
            'patriot_cc_ops/static/src/css/cc_ops.css',
            'patriot_cc_ops/static/src/css/pdf_viewer.css',
            # JavaScript (OWL Components)
            'patriot_cc_ops/static/src/js/cc_ops_dashboard.js',
            'patriot_cc_ops/static/src/js/pdf_viewer.js',
            # XML Templates
            'patriot_cc_ops/static/src/xml/cc_ops_dashboard.xml',
            'patriot_cc_ops/static/src/xml/pdf_viewer.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
