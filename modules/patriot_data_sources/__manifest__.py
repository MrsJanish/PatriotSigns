{
    'name': 'Patriot Data Sources',
    'version': '1.0',
    'summary': 'Map and visualize which fields come from which data sources',
    'description': '''
        Developer helper module for documenting data provenance.
        Track which fields are populated by which data sources
        (e.g., Email Bid Invite, ConstructConnect API, Manual Entry).
    ''',
    'category': 'Technical',
    'author': 'Omega Laser Design Inc',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/data_source_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'OPL-1',
}
