{
    'name': 'Patriot Panel Engine',
    'version': '1.0',
    'summary': 'Dynamic Pricing Calculator for Panel Signs',
    'description': """
        A specialized engine for calculating panel sign prices.
        - Configurable Material Costs
        - Labor and Overhead calculations
        - Integration with Sales Order lines
    """,
    'category': 'Sales',
    'author': 'Patriot Signs',
    'depends': ['sale_management', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'data/panel_data.xml',
        'views/panel_params_view.xml',
        # 'views/sale_views.xml',
        'views/product_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
