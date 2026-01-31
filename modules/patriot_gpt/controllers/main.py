from odoo import http
from odoo.http import request, Response
import json
import logging

_logger = logging.getLogger(__name__)

class PatriotGPTController(http.Controller):

    def _authenticate(self):
        """
        Authenticates using flexible methods:
        1. Basic Auth (Standard)
        2. Bearer Token usually containing 'login:password' (Composite Key)
        3. Simple API Key (falls back to lookup)
        
        Returns user_id if successful, None otherwise.
        """
        import base64
        
        try:
            # DEBUG: Dump ALL headers to see exactly what ChatGPT sends
            all_headers = dict(request.httprequest.headers)
            # Redact any sensitive values but show keys
            header_summary = {k: (v[:20] + '...' if len(v) > 20 else v) for k, v in all_headers.items()}
            _logger.info(f"GPT API AUTH: ALL HEADERS RECEIVED: {header_summary}")
            
            # DEBUG: Log all relevant headers
            auth_header = request.httprequest.headers.get('Authorization', '')
            api_key_header = request.httprequest.headers.get('X-Api-Key', '')
            _logger.info(f"GPT API AUTH: Authorization header present: {bool(auth_header)}, len={len(auth_header)}")
            _logger.info(f"GPT API AUTH: X-Api-Key header present: {bool(api_key_header)}, len={len(api_key_header)}")
            
            login = None
            password = None
            
            # 1. Handle Basic Auth
            if auth_header.startswith('Basic '):
                _logger.info("GPT API AUTH: Detected Basic Auth header")
                try:
                    decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
                    if ':' in decoded:
                        login, password = decoded.split(':', 1)
                        _logger.info(f"GPT API AUTH: Basic Auth decoded to login: {login}")
                except Exception as be:
                    _logger.warning(f"GPT API AUTH: Basic Auth decode failed: {str(be)}")
                    pass
            
            # 2. Handle Bearer (or just raw key in header)
            if not login:
                token = None
                if auth_header.startswith('Bearer '):
                    token = auth_header[7:]
                    _logger.info(f"GPT API AUTH: Extracted Bearer token, len={len(token)}")
                elif api_key_header:
                    token = api_key_header
                    _logger.info(f"GPT API AUTH: Using X-Api-Key header, len={len(token)}")
                
                if token:
                    # Check if user provided 'login:password' string as the key
                    if ':' in token:
                        login, password = token.split(':', 1)
                        _logger.info(f"GPT API AUTH: Token contains ':', split to login: {login}")
                    else:
                        # Logic for raw key lookup
                        # In Odoo 19, API keys are stored with raw key in 'name' field
                        _logger.info(f"GPT API AUTH: Raw token (no colon). Searching res.users.apikeys...")
                        _logger.info(f"GPT API AUTH: Token starts with: {token[:10]}... (len={len(token)})")
                        
                        try:
                            apikeys_model = request.env['res.users.apikeys'].sudo()
                            
                            # DEBUG: List all keys in database to understand structure
                            all_keys = apikeys_model.search([], limit=5)
                            _logger.info(f"GPT API AUTH: DEBUG Total keys in DB: {len(all_keys)}")
                            for key in all_keys:
                                # Log field names and partial values to understand structure
                                key_fields = key.read()[0] if key else {}
                                # Truncate sensitive fields
                                safe_fields = {k: (str(v)[:15] + '...' if len(str(v)) > 15 else v) for k, v in key_fields.items()}
                                _logger.info(f"GPT API AUTH: DEBUG Key record: {safe_fields}")
                            
                            # Search for API key by 'name' field (stores raw key in Odoo 19)
                            api_key_record = apikeys_model.search([
                                ('name', '=', token)
                            ], limit=1)
                            
                            _logger.info(f"GPT API AUTH: Search by 'name' returned {len(api_key_record)} records")
                            
                            if api_key_record:
                                uid = api_key_record.user_id.id
                                _logger.info(f"GPT API AUTH: SUCCESS! Found API Key for UID {uid}")
                                return uid
                            else:
                                _logger.warning("GPT API AUTH: No matching API key found in database")
                        except Exception as ex:
                            _logger.warning(f"GPT API AUTH: API Key search failed: {type(ex).__name__}: {str(ex)}")
                else:
                    _logger.warning("GPT API AUTH: No token extracted from headers")

            if not login or not password:
                _logger.warning("GPT API AUTH: Could not extract login/password from headers and Raw Key validation failed.")
                return None

            _logger.info(f"GPT API AUTH: Attempting res.users auth for login: {login}")

            # Find user by login first
            user = request.env['res.users'].sudo().search([('login', '=', login)], limit=1)
            if not user:
                _logger.warning(f"GPT API AUTH: User not found for login: {login}")
                return None
            
            # Odoo 19: Use _check_credentials with credential dict
            try:
                # _check_credentials expects a dict with 'password' key in v19
                user.sudo()._check_credentials({'password': password})
                _logger.info(f"GPT API AUTH: _check_credentials() SUCCESS for UID {user.id}")
                return user.id
            except Exception as auth_err:
                _logger.warning(f"GPT API AUTH: _check_credentials() failed: {auth_err}")
                
        except Exception as e:
            _logger.error(f"GPT API AUTH: Top-level exception: {type(e).__name__}: {str(e)}")
            return None

    def _response(self, data, status=200):
        return Response(
            json.dumps(data, default=str), 
            status=status, 
            mimetype='application/json'
        )

    @http.route(['/api/gpt/<string:model>', '/api/gpt/<string:model>/<int:id>'], type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_records(self, model, id=None, **kwargs):
        """
        GET /api/gpt/{model} - Search records
        GET /api/gpt/{model}/{id} - Read specific record
        Params: domain (json list), fields (json list), limit (int)
        """
        user_id = self._authenticate()
        if not user_id:
            return self._response({'error': 'Unauthorized'}, 401)
            
        # Switch environment to authenticated user
        request.update_env(user=user_id)
        
        try:
            if model not in request.env:
                return self._response({'error': f'Model {model} not found'}, 404)

            # Check access rights implicitly via ORM
            Model = request.env[model]
            
            if id:
                # Read single record
                fields = json.loads(kwargs.get('fields', '[]'))
                record = Model.browse(id)
                if not record.exists():
                     return self._response({'error': 'Record not found'}, 404)
                
                # If fields not specified, read standard fields? No, read return dict.
                # read() returns a list of dicts
                data = record.read(fields if fields else None)
                return self._response(data[0] if data else {})
            else:
                # Search records
                domain = json.loads(kwargs.get('domain', '[]'))
                fields = json.loads(kwargs.get('fields', '[]'))
                limit = int(kwargs.get('limit', 10))
                order = kwargs.get('order', '')
                
                records = Model.search_read(domain, fields=fields if fields else None, limit=limit, order=order)
                return self._response(records)

        except Exception as e:
            _logger.exception("GPT API Error:")
            return self._response({'error': str(e)}, 400)

    @http.route('/api/gpt/<string:model>', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def create_record(self, model, **kwargs):
        """
        POST /api/gpt/{model} - Create a new record
        Body: JSON dict of fields
        """
        user_id = self._authenticate()
        if not user_id:
            return self._response({'error': 'Unauthorized'}, 401)

        request.update_env(user=user_id)
        
        try:
            if model not in request.env:
                return self._response({'error': f'Model {model} not found'}, 404)

            data = json.loads(request.httprequest.data)
            new_record = request.env[model].create(data)
            
            return self._response({
                'id': new_record.id, 
                'display_name': new_record.display_name,
                'result': 'created'
            })
            
        except Exception as e:
            _logger.exception("GPT API Create Error:")
            return self._response({'error': str(e)}, 400)

    @http.route('/api/gpt/<string:model>/<int:id>', type='http', auth='public', methods=['PUT', 'PATCH'], csrf=False, cors='*')
    def update_record(self, model, id, **kwargs):
        """
        PUT/PATCH /api/gpt/{model}/{id} - Update a record
        Body: JSON dict of fields to update
        """
        user_id = self._authenticate()
        if not user_id:
            return self._response({'error': 'Unauthorized'}, 401)

        request.update_env(user=user_id)
        
        try:
            if model not in request.env:
                return self._response({'error': f'Model {model} not found'}, 404)

            data = json.loads(request.httprequest.data)
            record = request.env[model].browse(id)
            
            if not record.exists():
                return self._response({'error': 'Record not found'}, 404)
                
            record.write(data)
            
            return self._response({
                'id': record.id, 
                'display_name': record.display_name,
                'result': 'updated'
            })
            
        except Exception as e:
             _logger.exception("GPT API Update Error:")
             return self._response({'error': str(e)}, 400)

    @http.route('/api/gpt/schema/<string:model>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_model_schema(self, model, **kwargs):
        """
        GET /api/gpt/schema/{model} - Get complete model introspection
        
        Returns:
        - model_info: Basic model information (name, description, etc.)
        - fields: All field definitions with type, required, help text, etc.
        - automated_actions: All ir.actions.server (automated actions) linked to this model
        - server_actions: All server actions for this model
        - record_rules: Access rules for this model
        - views: Available views (tree, form, kanban, etc.)
        """
        user_id = self._authenticate()
        if not user_id:
            return self._response({'error': 'Unauthorized'}, 401)

        request.update_env(user=user_id)
        
        try:
            if model not in request.env:
                return self._response({'error': f'Model {model} not found'}, 404)

            Model = request.env[model]
            result = {
                'model': model,
                'model_info': {},
                'fields': {},
                'automated_actions': [],
                'server_actions': [],
                'record_rules': [],
                'views': []
            }
            
            # 1. Basic Model Info
            ir_model = request.env['ir.model'].sudo().search([('model', '=', model)], limit=1)
            if ir_model:
                result['model_info'] = {
                    'id': ir_model.id,
                    'name': ir_model.name,
                    'model': ir_model.model,
                    'info': ir_model.info or '',
                    'state': ir_model.state,
                    'transient': ir_model.transient,
                }
            
            # 2. All Fields with full metadata
            for field_name, field in Model._fields.items():
                field_info = {
                    'name': field_name,
                    'type': field.type,
                    'string': field.string or field_name,
                    'help': field.help or '',
                    'required': field.required,
                    'readonly': field.readonly,
                    'store': field.store,
                    'index': getattr(field, 'index', False),
                    'compute': field.compute or None,
                    'depends': list(field.depends) if field.depends else [],
                    'related': field.related or None,
                    'default': str(field.default) if field.default else None,
                }
                
                # Add relational field info
                if field.type in ('many2one', 'one2many', 'many2many'):
                    field_info['comodel_name'] = field.comodel_name
                if field.type == 'one2many':
                    field_info['inverse_name'] = field.inverse_name
                if field.type == 'selection':
                    # Get selection options
                    try:
                        sel = field.selection
                        if callable(sel):
                            sel = sel(Model)
                        field_info['selection'] = sel
                    except:
                        field_info['selection'] = []
                
                result['fields'][field_name] = field_info
            
            # 3. Automated Actions (ir.actions.server with base_automation)
            try:
                auto_actions = request.env['base.automation'].sudo().search([
                    ('model_id.model', '=', model)
                ])
                for action in auto_actions:
                    result['automated_actions'].append({
                        'id': action.id,
                        'name': action.name,
                        'trigger': action.trigger,
                        'trigger_field_ids': [f.name for f in action.trigger_field_ids] if action.trigger_field_ids else [],
                        'filter_domain': action.filter_domain or '[]',
                        'filter_pre_domain': action.filter_pre_domain or '[]',
                        'state': action.action_server_ids[0].state if action.action_server_ids else None,
                        'code': action.action_server_ids[0].code if action.action_server_ids and action.action_server_ids[0].state == 'code' else None,
                        'active': action.active,
                    })
            except Exception as e:
                _logger.warning(f"Could not fetch automated actions: {e}")
            
            # 4. Server Actions
            try:
                server_actions = request.env['ir.actions.server'].sudo().search([
                    ('model_id.model', '=', model)
                ])
                for action in server_actions:
                    result['server_actions'].append({
                        'id': action.id,
                        'name': action.name,
                        'state': action.state,
                        'code': action.code if action.state == 'code' else None,
                        'crud_model_id': action.crud_model_id.model if action.crud_model_id else None,
                    })
            except Exception as e:
                _logger.warning(f"Could not fetch server actions: {e}")
            
            # 5. Record Rules (ir.rule)
            try:
                rules = request.env['ir.rule'].sudo().search([
                    ('model_id.model', '=', model)
                ])
                for rule in rules:
                    result['record_rules'].append({
                        'id': rule.id,
                        'name': rule.name,
                        'domain_force': rule.domain_force or '[]',
                        'perm_read': rule.perm_read,
                        'perm_write': rule.perm_write,
                        'perm_create': rule.perm_create,
                        'perm_unlink': rule.perm_unlink,
                        'groups': [g.name for g in rule.groups] if rule.groups else ['All Users'],
                        'active': rule.active,
                    })
            except Exception as e:
                _logger.warning(f"Could not fetch record rules: {e}")
            
            # 6. Views
            try:
                views = request.env['ir.ui.view'].sudo().search([
                    ('model', '=', model)
                ], limit=20)
                for view in views:
                    result['views'].append({
                        'id': view.id,
                        'name': view.name,
                        'type': view.type,
                        'priority': view.priority,
                        'arch': view.arch if kwargs.get('include_arch') == '1' else '[use include_arch=1 to include]',
                    })
            except Exception as e:
                _logger.warning(f"Could not fetch views: {e}")
            
            # 7. Records Data (optional, use include_data=1 and limit=N)
            if kwargs.get('include_data') == '1':
                try:
                    limit = int(kwargs.get('limit', 1000))  # Default 1000 records max
                    domain = json.loads(kwargs.get('domain', '[]'))
                    records = Model.search_read(domain, limit=limit)
                    result['records'] = records
                    result['records_count'] = len(records)
                    result['records_total'] = Model.search_count(domain)
                except Exception as e:
                    _logger.warning(f"Could not fetch records: {e}")
                    result['records'] = []
                    result['records_error'] = str(e)
            
            return self._response(result)

        except Exception as e:
            _logger.exception("GPT API Schema Error:")
            return self._response({'error': str(e)}, 400)
