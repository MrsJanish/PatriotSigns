{
    'name': 'Patriot Submittals',
    'version': '19.0.1.0.0',
    'category': 'Project',
    'summary': 'Submittal and shop drawing workflow',
    'description': """
Patriot Submittals Module
=========================

Submittal workflow for sign projects:
- Submittal package creation
- Shop drawing management
- Revision tracking
- Approval workflow (Submit → Review → Approved/Revise)
- RFI (Request for Information) tracking
- Transmittal generation

Follows standard AIA submittal procedures.
    """,
    'author': 'Patriot Signs',
    'website': 'https://patriotsigns.com',
    'depends': [
        'patriot_projects',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/submittal_views.xml',
        'views/rfi_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
