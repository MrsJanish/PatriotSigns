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
            auth_header = request.httprequest.headers.get('Authorization', '')
            login = None
            password = None
            
            # 1. Handle Basic Auth
            if auth_header.startswith('Basic '):
                try:
                    decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
                    if ':' in decoded:
                        login, password = decoded.split(':', 1)
                except:
                    pass
            
            # 2. Handle Bearer (or just raw key in header)
            if not login:
                token = ''
                if auth_header.startswith('Bearer '):
                    token = auth_header[7:]
                else:
                    token = request.httprequest.headers.get('X-Api-Key')
                
                if token:
                    # Check if user provided 'login:password' string as the key
                    if ':' in token:
                        login, password = token.split(':', 1)
                    else:
                        # Logic for raw key lookup
                        # Try to validate as Odoo API Key directly
                        if hasattr(request.env['res.users.apikeys'], '_check_api_key'):
                            try:
                                # _check_api_key returns user_id (int) or raises AccessDenied
                                uid = request.env['res.users.apikeys']._check_api_key(token)
                                if uid:
                                    _logger.info(f"GPT API: Validated Odoo API Key for UID {uid}")
                                    return uid
                            except Exception as ex:
                                _logger.warning(f"GPT API: API Key validation failed: {str(ex)}")
                                pass

            if not login or not password:
                _logger.warning("GPT API: Could not extract login/password from headers and Raw Key validation failed.")
                return None

            _logger.info(f"GPT API: Auth attempt for login: {login}")

            # Authenticate with extracted credentials
            uid = request.session.authenticate(request.db, login=login, password=password)
            
            if uid:
                _logger.info(f"GPT API: Auth success for UID {uid}")
            else:
                _logger.warning("GPT API: Auth returned distinct False/None")
                
            return uid
                
        except Exception as e:
            _logger.error(f"GPT API Auth Failed with Exception: {type(e).__name__}: {str(e)}")
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
