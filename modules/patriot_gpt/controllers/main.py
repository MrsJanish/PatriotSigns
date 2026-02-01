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
            
            # Direct password verification - must use SQL since ORM protects password field
            try:
                from passlib.context import CryptContext
                # Odoo's password context supports bcrypt and pbkdf2_sha512
                crypt_context = CryptContext(schemes=['pbkdf2_sha512', 'bcrypt'])
                
                # Get the stored password hash via raw SQL (ORM won't expose it)
                request.env.cr.execute(
                    "SELECT password FROM res_users WHERE id = %s",
                    (user.id,)
                )
                result = request.env.cr.fetchone()
                stored_hash = result[0] if result else None
                
                if not stored_hash:
                    _logger.warning(f"GPT API AUTH: No password hash in DB for user {login}")
                    return None
                
                _logger.info(f"GPT API AUTH: Found hash for {login}, verifying...")
                
                # Verify the password against the stored hash
                if crypt_context.verify(password, stored_hash):
                    _logger.info(f"GPT API AUTH: Password verified SUCCESS for UID {user.id}")
                    return user.id
                else:
                    _logger.warning(f"GPT API AUTH: Password verification FAILED for {login}")
            except Exception as auth_err:
                _logger.warning(f"GPT API AUTH: SQL/passlib verification failed: {auth_err}")
                
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
                fields_raw = kwargs.get('fields', '')
                if isinstance(fields_raw, str):
                    if fields_raw.startswith('['):
                        try:
                            fields = json.loads(fields_raw)
                        except json.JSONDecodeError:
                            fields = []
                    elif fields_raw:
                        fields = [f.strip() for f in fields_raw.split(',')]
                    else:
                        fields = []
                else:
                    fields = fields_raw if fields_raw else []
                    
                record = Model.browse(id)
                if not record.exists():
                     return self._response({'error': 'Record not found'}, 404)
                
                data = record.read(fields if fields else None)
                return self._response(data[0] if data else {})
            else:
                # Search records
                _logger.info(f"GPT API SEARCH: model={model}, kwargs={kwargs}")
                
                # Parse domain - ChatGPT may send with single quotes (not valid JSON)
                domain_raw = kwargs.get('domain', '[]')
                if isinstance(domain_raw, str):
                    # Replace single quotes with double quotes for JSON parsing
                    domain_str = domain_raw.replace("'", '"')
                    try:
                        domain = json.loads(domain_str)
                    except json.JSONDecodeError:
                        domain = []  # Fallback to empty domain
                        _logger.warning(f"GPT API: Could not parse domain: {domain_raw}")
                else:
                    domain = domain_raw
                
                # Parse fields - ChatGPT may send comma-separated string like "name,email"
                fields_raw = kwargs.get('fields', '')
                if isinstance(fields_raw, str):
                    if fields_raw.startswith('['):
                        # It's a JSON array
                        try:
                            fields = json.loads(fields_raw)
                        except json.JSONDecodeError:
                            fields = []
                    elif fields_raw:
                        # It's a comma-separated string
                        fields = [f.strip() for f in fields_raw.split(',')]
                    else:
                        fields = []
                else:
                    fields = fields_raw if fields_raw else []
                
                limit = int(kwargs.get('limit', 10))
                order = kwargs.get('order', '')
                
                _logger.info(f"GPT API SEARCH: domain={domain}, fields={fields}, limit={limit}")
                
                records = Model.search_read(domain, fields=fields if fields else None, limit=limit, order=order if order else None)
                _logger.info(f"GPT API SEARCH: Found {len(records)} records")
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
        
        Params:
        - fields_only: "1" to return compact field list (name, type, string only)
        - field_types: comma-separated types to filter (e.g., "many2one,one2many")
        - fields_limit: max number of fields to return (default: all)
        - fields_offset: offset for field pagination
        - skip_automations: "1" to skip automations/views (faster for large models)
        
        Returns:
        - model_info: Basic model information (name, description, etc.)
        - fields: Field definitions (full or compact based on fields_only)
        - fields_total: Total number of fields in model
        - automated_actions: All ir.actions.server (automated actions) linked to this model
        - server_actions: All server actions for this model
        - record_rules: Access rules for this model
        - views: Available views (tree, form, kanban, etc.)
        """
        user_id = self._authenticate()
        if not user_id:
            return self._response({'error': 'Unauthorized'}, 401)

        request.update_env(user=user_id)
        
        # Parse filtering options
        fields_only = kwargs.get('fields_only', '0') == '1'
        field_types_raw = kwargs.get('field_types', '')
        field_types = [t.strip() for t in field_types_raw.split(',')] if field_types_raw else []
        fields_limit = int(kwargs.get('fields_limit', 0)) or None  # 0 means no limit
        fields_offset = int(kwargs.get('fields_offset', 0))
        skip_automations = kwargs.get('skip_automations', '0') == '1'
        
        try:
            if model not in request.env:
                return self._response({'error': f'Model {model} not found'}, 404)

            Model = request.env[model]
            result = {
                'model': model,
                'model_info': {},
                'fields': {},
                'fields_total': 0,
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
            
            # 2. All Fields with filtering/pagination
            all_fields = list(Model._fields.items())
            result['fields_total'] = len(all_fields)
            
            # Filter by type if requested
            if field_types:
                all_fields = [(name, field) for name, field in all_fields if field.type in field_types]
            
            # Apply offset and limit
            if fields_offset:
                all_fields = all_fields[fields_offset:]
            if fields_limit:
                all_fields = all_fields[:fields_limit]
            
            for field_name, field in all_fields:
                if fields_only:
                    # Compact mode - just essentials
                    field_info = {
                        'name': field_name,
                        'type': field.type,
                        'string': field.string or field_name,
                        'required': field.required,
                    }
                    if field.type in ('many2one', 'one2many', 'many2many'):
                        field_info['comodel_name'] = field.comodel_name
                else:
                    # Full mode - all metadata
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
                        'depends': list(getattr(field, '_depends', [])) if getattr(field, '_depends', None) else [],
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
            
            # Skip remaining sections if skip_automations is set (for large models)
            if skip_automations:
                return self._response(result)
            
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

    # =========================================================================
    # DELETE Record
    # =========================================================================
    @http.route('/api/gpt/<string:model>/<int:id>', type='http', auth='public', methods=['DELETE'], csrf=False, cors='*')
    def delete_record(self, model, id, **kwargs):
        """
        DELETE /api/gpt/{model}/{id} - Delete a record
        """
        user_id = self._authenticate()
        if not user_id:
            return self._response({'error': 'Unauthorized'}, 401)

        request.update_env(user=user_id)
        
        try:
            if model not in request.env:
                return self._response({'error': f'Model {model} not found'}, 404)

            record = request.env[model].browse(id)
            if not record.exists():
                return self._response({'error': 'Record not found'}, 404)
            
            display_name = record.display_name
            record.unlink()
            
            return self._response({
                'id': id,
                'display_name': display_name,
                'result': 'deleted'
            })
            
        except Exception as e:
            _logger.exception("GPT API Delete Error:")
            return self._response({'error': str(e)}, 400)

    # =========================================================================
    # Call Method (Button/Workflow simulation)
    # =========================================================================
    @http.route('/api/gpt/<string:model>/<int:id>/call/<string:method>', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def call_method(self, model, id, method, **kwargs):
        """
        POST /api/gpt/{model}/{id}/call/{method} - Call a method on a record
        Simulates clicking a button or triggering a workflow action.
        Body: JSON dict of method arguments (optional)
        """
        user_id = self._authenticate()
        if not user_id:
            return self._response({'error': 'Unauthorized'}, 401)

        request.update_env(user=user_id)
        
        try:
            if model not in request.env:
                return self._response({'error': f'Model {model} not found'}, 404)

            record = request.env[model].browse(id)
            if not record.exists():
                return self._response({'error': 'Record not found'}, 404)
            
            # Get method arguments from body
            try:
                body = json.loads(request.httprequest.data or '{}')
            except:
                body = {}
            
            # Security: Only allow calling methods that don't start with underscore
            # Exception: whitelist common private methods that are safe and needed
            ALLOWED_PRIVATE_METHODS = {
                '_create_invoices',  # sale.order - create invoices
                '_compute_access_url',  # many models
                '_onchange_partner_id',  # many models
            }
            if method.startswith('_') and method not in ALLOWED_PRIVATE_METHODS:
                return self._response({'error': f'Cannot call private method: {method}'}, 403)
            
            if not hasattr(record, method):
                return self._response({'error': f'Method {method} not found on {model}'}, 404)
            
            method_func = getattr(record, method)
            if not callable(method_func):
                return self._response({'error': f'{method} is not callable'}, 400)
            
            _logger.info(f"GPT API CALL_METHOD: {model}/{id}.{method}({body})")
            
            # Call the method with arguments if provided
            if body:
                result = method_func(**body)
            else:
                result = method_func()
            
            # Handle different return types
            if hasattr(result, 'id'):
                # It's a record
                return self._response({
                    'success': True,
                    'method': method,
                    'result_id': result.id,
                    'result_model': result._name if hasattr(result, '_name') else None
                })
            elif isinstance(result, dict):
                # It's a dict (possibly action)
                return self._response({
                    'success': True,
                    'method': method,
                    'result': result
                })
            else:
                return self._response({
                    'success': True,
                    'method': method,
                    'result': str(result) if result is not None else None
                })
            
        except Exception as e:
            _logger.exception("GPT API Call Method Error:")
            return self._response({'error': str(e)}, 400)

    # =========================================================================
    # Batch Operations (Multiple operations in one call)
    # =========================================================================
    @http.route('/api/gpt/batch', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def batch_operations(self, **kwargs):
        """
        POST /api/gpt/batch - Execute multiple operations in one HTTP call
        Body: { "operations": [ { "op": "read", "model": "res.partner", "id": 1 }, ... ] }
        Supported ops: read, search, schema, create, update, delete, call
        """
        user_id = self._authenticate()
        if not user_id:
            return self._response({'error': 'Unauthorized'}, 401)

        request.update_env(user=user_id)
        
        try:
            body = json.loads(request.httprequest.data)
            operations = body.get('operations', [])
            results = []
            
            for op in operations[:10]:  # Max 10 operations per batch
                op_type = op.get('op', 'read')
                model = op.get('model')
                
                try:
                    if model not in request.env:
                        results.append({'error': f'Model {model} not found'})
                        continue
                    
                    Model = request.env[model]
                    
                    if op_type == 'read':
                        record = Model.browse(op.get('id'))
                        fields = op.get('fields')
                        data = record.read(fields if fields else None)
                        results.append({'data': data[0] if data else {}})
                    
                    elif op_type == 'search':
                        domain = op.get('domain', [])
                        fields = op.get('fields')
                        limit = op.get('limit', 10)
                        records = Model.search_read(domain, fields=fields, limit=limit)
                        results.append({'data': records})
                    
                    elif op_type == 'schema':
                        fields_only = op.get('fields_only', False)
                        field_data = {}
                        for field_name, field in Model._fields.items():
                            if fields_only:
                                field_data[field_name] = {'type': field.type, 'string': field.string}
                            else:
                                field_data[field_name] = {
                                    'type': field.type,
                                    'string': field.string,
                                    'required': field.required,
                                    'comodel_name': getattr(field, 'comodel_name', None)
                                }
                        results.append({'fields': field_data, 'total': len(field_data)})
                    
                    elif op_type == 'create':
                        new_record = Model.create(op.get('values', {}))
                        results.append({'id': new_record.id, 'result': 'created'})
                    
                    elif op_type == 'update':
                        record = Model.browse(op.get('id'))
                        record.write(op.get('values', {}))
                        results.append({'id': op.get('id'), 'result': 'updated'})
                    
                    elif op_type == 'delete':
                        record = Model.browse(op.get('id'))
                        record.unlink()
                        results.append({'id': op.get('id'), 'result': 'deleted'})
                    
                    elif op_type == 'call':
                        record = Model.browse(op.get('id'))
                        method = op.get('method')
                        method_args = op.get('args', {})
                        if not method.startswith('_') and hasattr(record, method):
                            result = getattr(record, method)(**method_args)
                            results.append({'result': str(result) if result else None})
                        else:
                            results.append({'error': f'Invalid method: {method}'})
                    
                    else:
                        results.append({'error': f'Unknown operation: {op_type}'})
                        
                except Exception as op_error:
                    results.append({'error': str(op_error)})
            
            return self._response({'results': results})
            
        except Exception as e:
            _logger.exception("GPT API Batch Error:")
            return self._response({'error': str(e)}, 400)

    # =========================================================================
    # Module Upgrade (DevOps)
    # =========================================================================
    @http.route('/api/gpt/upgrade', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def upgrade_modules(self, **kwargs):
        """
        POST /api/gpt/upgrade - Upgrade specified modules
        Body: { "modules": ["patriot_base", "patriot_gpt"] }
        """
        user_id = self._authenticate()
        if not user_id:
            return self._response({'error': 'Unauthorized'}, 401)

        request.update_env(user=user_id)
        
        try:
            body = json.loads(request.httprequest.data)
            module_names = body.get('modules', [])
            
            if not module_names:
                return self._response({'error': 'No modules specified'}, 400)
            
            # Find the modules
            modules = request.env['ir.module.module'].sudo().search([
                ('name', 'in', module_names)
            ])
            
            if not modules:
                return self._response({'error': f'Modules not found: {module_names}'}, 404)
            
            # Set modules to "to upgrade" state
            modules.button_immediate_upgrade()
            
            return self._response({
                'success': True,
                'modules': module_names,
                'message': f'Modules scheduled for upgrade: {", ".join(module_names)}'
            })
            
        except Exception as e:
            _logger.exception("GPT API Upgrade Error:")
            return self._response({'error': str(e)}, 400)

    # =========================================================================
    # Server Logs Access (DevOps)
    # =========================================================================
    @http.route('/api/gpt/logs', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_server_logs(self, **kwargs):
        """
        GET /api/gpt/logs - Get recent server log entries
        Params: lines (int, default 50), level (str: error/warning/info/all)
        
        Note: This reads from ir.logging if available, otherwise from Odoo.sh logs
        """
        user_id = self._authenticate()
        if not user_id:
            return self._response({'error': 'Unauthorized'}, 401)

        request.update_env(user=user_id)
        
        try:
            lines = int(kwargs.get('lines', 50))
            level = kwargs.get('level', 'all')
            
            # Try to read from ir.logging (database logging)
            domain = []
            if level != 'all':
                level_map = {'error': 'ERROR', 'warning': 'WARNING', 'info': 'INFO'}
                odoo_level = level_map.get(level, level.upper())
                domain.append(('level', '=', odoo_level))
            
            logs = request.env['ir.logging'].sudo().search(
                domain, 
                limit=lines, 
                order='create_date desc'
            )
            
            log_entries = []
            for log in logs:
                log_entries.append({
                    'timestamp': log.create_date,
                    'level': log.level,
                    'name': log.name,
                    'func': log.func,
                    'message': log.message,
                    'path': log.path,
                    'line': log.line,
                })
            
            return self._response({
                'logs': log_entries,
                'count': len(log_entries),
                'level_filter': level
            })
            
        except Exception as e:
            # If ir.logging not available (not enabled), return helpful message
            return self._response({
                'error': str(e),
                'hint': 'Database logging may not be enabled. Enable via log_db in odoo.conf.'
            }, 400)

    # =========================================================================
    # Get View Definition (Navigation)
    # =========================================================================
    @http.route('/api/gpt/get_view', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_view(self, **kwargs):
        """
        GET /api/gpt/get_view - Get view definition for a model
        Params: model (required), view_type (form/tree/kanban), view_id (optional)
        """
        user_id = self._authenticate()
        if not user_id:
            return self._response({'error': 'Unauthorized'}, 401)

        request.update_env(user=user_id)
        
        try:
            model = kwargs.get('model')
            view_type = kwargs.get('view_type', 'form')
            view_id = int(kwargs.get('view_id', 0)) or False
            
            if not model:
                return self._response({'error': 'model parameter required'}, 400)
            
            if model not in request.env:
                return self._response({'error': f'Model {model} not found'}, 404)
            
            Model = request.env[model]
            
            # Get view using fields_view_get (standard Odoo method)
            view_data = Model.get_view(view_id=view_id, view_type=view_type)
            
            return self._response({
                'model': model,
                'view_type': view_type,
                'view_id': view_data.get('view_id'),
                'arch': view_data.get('arch'),
                'fields': view_data.get('fields', {}),
                'name': view_data.get('name'),
                'toolbar': view_data.get('toolbar', {}),
            })
            
        except Exception as e:
            _logger.exception("GPT API Get View Error:")
            return self._response({'error': str(e)}, 400)

    # =========================================================================
    # Onchange Simulation (Navigation)
    # =========================================================================
    @http.route('/api/gpt/<string:model>/onchange', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def run_onchange(self, model, **kwargs):
        """
        POST /api/gpt/{model}/onchange - Simulate onchange for a field
        Body: { "values": {...}, "field_changed": "partner_id" }
        Returns the values that would be updated by the onchange
        """
        user_id = self._authenticate()
        if not user_id:
            return self._response({'error': 'Unauthorized'}, 401)

        request.update_env(user=user_id)
        
        try:
            if model not in request.env:
                return self._response({'error': f'Model {model} not found'}, 404)
            
            body = json.loads(request.httprequest.data)
            values = body.get('values', {})
            field_changed = body.get('field_changed')
            
            if not field_changed:
                return self._response({'error': 'field_changed parameter required'}, 400)
            
            Model = request.env[model]
            
            # Create a new record in memory and trigger onchange
            record = Model.new(values)
            
            # Find and call onchange method
            onchange_method = f'_onchange_{field_changed}'
            onchange_results = {}
            
            if hasattr(record, onchange_method):
                getattr(record, onchange_method)()
                # Read back changed values
                for field_name in Model._fields:
                    new_val = getattr(record, field_name, None)
                    if field_name in values:
                        old_val = values.get(field_name)
                        # Compare and include if changed
                        try:
                            if hasattr(new_val, 'id'):
                                if new_val.id != old_val:
                                    onchange_results[field_name] = new_val.id
                            elif new_val != old_val:
                                onchange_results[field_name] = new_val
                        except:
                            pass
            
            return self._response({
                'model': model,
                'field_changed': field_changed,
                'suggested_changes': onchange_results,
            })
            
        except Exception as e:
            _logger.exception("GPT API Onchange Error:")
            return self._response({'error': str(e)}, 400)

    # =========================================================================
    # Execute Server Action (Navigation)
    # =========================================================================
    @http.route('/api/gpt/ir.actions.server/run', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def run_server_action(self, **kwargs):
        """
        POST /api/gpt/ir.actions.server/run - Execute a server action
        Body: { "action_id": 123, "model": "sale.order", "record_ids": [1, 2, 3] }
        """
        user_id = self._authenticate()
        if not user_id:
            return self._response({'error': 'Unauthorized'}, 401)

        request.update_env(user=user_id)
        
        try:
            body = json.loads(request.httprequest.data)
            action_id = body.get('action_id')
            model = body.get('model')
            record_ids = body.get('record_ids', [])
            
            if not action_id:
                return self._response({'error': 'action_id required'}, 400)
            
            action = request.env['ir.actions.server'].browse(action_id)
            if not action.exists():
                return self._response({'error': f'Action {action_id} not found'}, 404)
            
            # Set up context for action execution
            context = dict(request.env.context)
            if model and record_ids:
                context['active_model'] = model
                context['active_ids'] = record_ids
                context['active_id'] = record_ids[0] if record_ids else False
            
            # Execute the action
            result = action.with_context(context).run()
            
            return self._response({
                'success': True,
                'action_id': action_id,
                'action_name': action.name,
                'result': result if isinstance(result, dict) else str(result) if result else None
            })
            
        except Exception as e:
            _logger.exception("GPT API Run Action Error:")
            return self._response({'error': str(e)}, 400)

    # =========================================================================
    # List Available Models (Utility)
    # =========================================================================
    @http.route('/api/gpt/models', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def list_models(self, **kwargs):
        """
        GET /api/gpt/models - List available models
        Params: prefix (filter by prefix, e.g., "ps." or "sale.")
        """
        user_id = self._authenticate()
        if not user_id:
            return self._response({'error': 'Unauthorized'}, 401)

        request.update_env(user=user_id)
        
        try:
            prefix = kwargs.get('prefix', '')
            limit = int(kwargs.get('limit', 50))
            
            domain = []
            if prefix:
                domain.append(('model', '=like', f'{prefix}%'))
            
            models = request.env['ir.model'].sudo().search(domain, limit=limit, order='model')
            
            result = []
            for m in models:
                result.append({
                    'model': m.model,
                    'name': m.name,
                    'transient': m.transient,
                    'info': m.info or '',
                })
            
            return self._response({
                'models': result,
                'count': len(result),
            })
            
        except Exception as e:
            return self._response({'error': str(e)}, 400)

    # =========================================================================
    # Health Check
    # =========================================================================
    @http.route('/api/gpt/health', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def health_check(self, **kwargs):
        """
        GET /api/gpt/health - Simple health check (no auth required for monitoring)
        """
        return self._response({
            'status': 'ok',
            'module': 'patriot_gpt',
            'version': '2.0.0',
            'timestamp': str(request.env.cr.now()),
        })

