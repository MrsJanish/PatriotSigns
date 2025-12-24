{
    'name': 'Patriot Production',
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Sign production and MRP integration',
    'description': """
Patriot Production Module
=========================

Production management for sign manufacturing:
- Production orders from approved submittals
- Work center routing (Design, Fabrication, Assembly, QC)
- Material tracking and inventory
- Quality control checkpoints
- Packaging and shipping preparation

Integrates with Odoo MRP for manufacturing operations.
    """,
    'author': 'Patriot Signs',
    'website': 'https://patriotsigns.com',
    'depends': [
        'mrp',
        'patriot_submittals',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/work_centers.xml',
        'views/production_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
