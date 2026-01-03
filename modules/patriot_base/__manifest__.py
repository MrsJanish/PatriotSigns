{
    'name': 'Omega Signs Base',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Base configuration and reference tables for Omega Signs Co',
    'description': """
Omega Signs Base Module
=========================

Foundation module providing:
- Sign category classifications (PAN, PLQ, DCHA, etc.)
- Sign subtype templates 
- Dimension lookup tables
- Partner extensions (GC, Owner, Architect tags)

This module must be installed before other Omega Signs modules.
    """,
    'author': 'Omega Signs Co',
    'website': 'https://omegasignsco.com',
    'depends': [
        'base',
        'contacts',
        'product',
        'uom',
        'hr',
        'sale_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/partner_categories.xml',
        'data/sign_categories.xml',
        'data/sign_subtypes.xml',
        'data/sign_dimensions.xml',
        'data/sign_products.xml',
        'data/labor_rates.xml',
        'data/employees.xml',
        'data/mock_partners.xml',
        'views/sign_category_views.xml',
        'views/sign_subtype_views.xml',
        'views/sign_dimension_views.xml',
        'views/res_partner_views.xml',
        'views/menu.xml',
        'views/menu_unified.xml',
    ],
    'installable': True,
    'application': False,  # Not a standalone app, just foundation
    'auto_install': False,
    'license': 'LGPL-3',
}
