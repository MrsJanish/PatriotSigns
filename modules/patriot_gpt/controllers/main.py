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
                        
                        try:
                            apikeys_model = request.env['res.users.apikeys'].sudo()
                            # Search for API key by 'name' field (stores raw key in Odoo 19)
                            api_key_record = apikeys_model.search([
                                ('name', '=', token)
                            ], limit=1)
                            
                            _logger.info(f"GPT API AUTH: Search returned {len(api_key_record)} records")
                            
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

            _logger.info(f"GPT API AUTH: Attempting session.authenticate for login: {login}")

            # Authenticate with extracted credentials
            uid = request.session.authenticate(request.db, login=login, password=password)
            
            if uid:
                _logger.info(f"GPT API AUTH: session.authenticate SUCCESS for UID {uid}")
            else:
                _logger.warning("GPT API AUTH: session.authenticate returned False/None")
                
            return uid
                
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
