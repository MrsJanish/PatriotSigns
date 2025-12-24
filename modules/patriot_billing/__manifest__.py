{
    'name': 'Patriot Billing',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Pay applications and billing management',
    'description': """
Patriot Billing Module
======================

Billing management for sign projects:
- Pay application (AIA G702/G703) creation
- Progress billing by line item
- Retainage tracking
- Invoice generation
- Payment tracking
- SOV (Schedule of Values) management

Integrates with Odoo Accounting for invoicing.
    """,
    'author': 'Patriot Signs',
    'website': 'https://patriotsigns.com',
    'depends': [
        'account',
        'patriot_field_service',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sov_template.xml',
        'views/pay_application_views.xml',
        'views/sov_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
