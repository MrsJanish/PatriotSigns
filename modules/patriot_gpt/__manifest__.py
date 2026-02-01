{
    'name': 'Patriot GPT API Connector',
    'version': '2.0',
    'summary': 'Full REST API for AI Agents (ChatGPT, Gemini, MCP)',
    'description': '''
        Exposes comprehensive REST endpoints for AI agents to interact with Odoo:
        - CRUD operations (GET, POST, PUT, DELETE)
        - Model introspection with field-level detail
        - Method calling (button/workflow simulation)
        - Batch operations (multi-op in single HTTP call)
        - Module upgrade trigger (DevOps)
        - Server log access (DevOps)
        - View definitions (Navigation)
        - Onchange simulation (Navigation)
        - Server action execution
        
        Authenticates via native Odoo API Keys or login:password.
    ''',
    'category': 'Technical',
    'author': 'Omega Laser Design Inc',
    'depends': ['base', 'web', 'base_automation'],
    'data': [],
    'installable': True,
    'application': False,
    'license': 'OPL-1',
}

