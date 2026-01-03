{
    'name': 'Omega Signs CRM',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'CRM extensions for sign project management',
    'description': """
Omega Signs CRM Module
========================

Extends Odoo CRM with:
- ConstructConnect integration fields
- Bid date and bid type tracking
- Project party links (GC, Owner, Architect)
- Project location fields
- Document tracking
- Sign project workflow stages
- Project profitability tracking
- Timesheet integration for labor cost tracking

This module integrates the CC Ops dashboard with Odoo's native CRM pipeline.
    """,
    'author': 'Omega Signs Co',
    'website': 'https://omegasignsco.com',
    'depends': [
        'crm',
        'hr_timesheet',
        'patriot_base',
    ],
    'data': [
        'security/ir.model.access.csv',

        'data/crm_cleanup.xml',
        'data/crm_stages.xml',
        'data/mock_projects.xml',
        'views/crm_lead_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'demo': [
        'demo/demo_data.xml',
    ],
}
