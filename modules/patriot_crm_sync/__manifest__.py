{
    'name': 'Patriot CRM-Project Sync',
    'version': '1.0',
    'summary': 'Bidirectional sync between CRM leads and Projects',
    'description': '''
        Automatically creates a Project when a CRM lead is marked as Won,
        and keeps fields synchronized bidirectionally between the CRM lead
        and its linked Project for the full project lifespan.

        Features:
        - Auto-create project with full field mapping on Won
        - CRM → Project field sync (20+ fields)
        - Project → CRM field sync (reverse)
        - Sign types & locations auto-linked to new projects
        - Infinite loop protection via context flag
        - Installation task + bidding timesheet migration
    ''',
    'category': 'Sales/CRM',
    'author': 'Omega Laser Design Inc',
    'depends': ['crm', 'project', 'sale_management', 'sale_project'],
    'data': [
        'data/disable_studio_automations.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'OPL-1',
}
