{
    'name': 'Construct Connect Opportunities',
    'version': '19.0.3.0.0',
    'summary': 'Automate ITB ingestion from ConstructConnect with PDF viewer and sign schedule extraction',
    'description': """
        This module monitors incoming emails for ConstructConnect ITB notifications,
        fetches project details via API, and stores construction documents.
        
        Features:
        - Glassmorphism dashboard with expandable project cards
        - PDF viewer with drag-drop split view
        - Lasso bookmark tool for sign identification
        - Sign type management with bookmark navigation
        - Excel sign schedule export
        - Two theme options (Light & Aurora Borealis)
    """,
    'category': 'Sales/CRM',
    'author': 'Patriot Signs',
    'depends': ['mail', 'crm'],
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
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
