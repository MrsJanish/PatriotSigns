{
    'name': 'Patriot Projects',
    'version': '19.0.1.0.0',
    'category': 'Project',
    'summary': 'Project management for sign contracts',
    'description': """
Patriot Projects Module
=======================

Project management for awarded sign contracts:
- Convert won CRM leads to projects
- Project stages matching Workflow.drawio
- Contract tracking and milestones
- Insurance/COI tracking
- Link to submittals, production, installation

This module bridges CRM (bidding) to execution (production/install).
    """,
    'author': 'Patriot Signs',
    'website': 'https://patriotsigns.com',
    'depends': [
        'project',
        'hr_timesheet',
        'patriot_signage',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'data/project_stages.xml',
        'data/service_products.xml',
        'data/project_template.xml',
        'views/project_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
