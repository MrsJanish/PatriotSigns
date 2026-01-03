{
    'name': 'Construct Connect Opportunities',
    'version': '19.0.4.0.0',
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
        
        Now integrated with:
        - patriot_crm: CRM lead extensions
        - patriot_signage: Sign type and instance management
    """,
    'category': 'Sales/CRM',
    'author': 'Omega Signs Co',
    'depends': [
        'patriot_signage',  # Pulls in patriot_crm and patriot_base
    ],
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
    'data': [
        'security/ir.model.access.csv',
        # NOTE: cc_opportunity_views.xml removed - using crm.lead views now
        'views/menus.xml',
        'data/ir_config_parameter.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # CSS
            'patriot_cc_ops/static/src/css/cc_ops.css',
            'patriot_cc_ops/static/src/css/sign_tally.css',
            # JavaScript (OWL Components)
            'patriot_cc_ops/static/src/js/cc_ops_dashboard.js',
            'patriot_cc_ops/static/src/js/sign_tally.js',
            # XML Templates
            'patriot_cc_ops/static/src/xml/cc_ops_dashboard.xml',
            'patriot_cc_ops/static/src/xml/sign_tally.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
