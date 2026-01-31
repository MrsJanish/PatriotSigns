from odoo import http
from odoo.http import request, Response
import json
import logging

_logger = logging.getLogger(__name__)

class PatriotGPTController(http.Controller):

    def _authenticate(self):
        """
        Authenticates using Odoo's native API Keys via session.authenticate.
        Expects 'X-Api-Key' or 'Authorization: Bearer <key>'.
        Returns user_id if successful, None otherwise.
        """
        try:
            # DEBUG LOGGING
            _logger.info(f"GPT API: Auth attempt. DB: {request.db}")
            
            key = request.httprequest.headers.get('X-Api-Key')
            if not key:
                auth_header = request.httprequest.headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    key = auth_header[7:]
            
            if not key:
                _logger.warning("GPT API: Missing API Key in headers")
                return None
            
            _logger.info(f"GPT API: Key received (len: {len(key)})")

            # Native Odoo API Key validation logic for Controllers
            # 1. Find the API Key record (hashed match)
            # 2. Extract the User (Login)
            # 3. Authenticate Session with (db, login, key)

            # Note: stored keys are hashed. We need to find the user efficiently.
            # In Odoo, res.users.apikeys stores a hash. Check via `_check_api_key` if available, 
            # otherwise we must use the standard lookup if possible.
            # But wait, we cannot search by unhashed key if it's hashed.
            # actually, `_check_api_key` is the only way to verify it if we don't know the user.
            # But wait, `res.users.apikeys` usually has `_check_api_key` in recent versions.
            # If not, how does Odoo do it? Odoo iterates? No.
            # Perplexity said: "apikey = request.env['res.users.apikeys'].sudo().search([('key', '=', key)])"
            # This implies the key is stored as-is? OR we are lucky.
            # Let's try to find it. AND verify if `_check_api_key` is available.
            # If `_check_api_key` is missing, we might have to try to find the user another way?
            # Actually, `res.users.apikeys` usually has a `key` field that MIGHT be the hash (or not).
            # Let's try to find the user via `_check_api_key` first (as suggested in my first attempt, but I removed it).
            # The issue with my first attempt might have been method visibility or `request.env` user.
            
            # Let's try the safest "Odoo internal" way:
            # `request.env['res.users.apikeys']._check_api_key(key)` returns the user_id.
            # Attempt 1: Check if `_check_api_key` exists.
            
            uid = None
            if hasattr(request.env['res.users.apikeys'], '_check_api_key'):
                 try:
                     uid = request.env['res.users.apikeys']._check_api_key(key)
                 except:
                     uid = None
            
            if not uid:
                # Attempt 2: Direct Search (if keys are not hashed - unlikely in v19, but worth a shot)
                # Or if `key` field matches (sometimes it's first chars).
                # Actually, there IS a way to authenticate with just a key if we use `res.users`? 
                pass

            if uid:
                _logger.info(f"GPT API: Found UID {uid} from key lookup.")
                # Now we have UID, we can get the login
                user = request.env['res.users'].sudo().browse(uid)
                # FULL AUTHENTICATION
                request.session.authenticate(request.db, login=user.login, password=key)
                return uid
            
            _logger.warning("GPT API: key lookup failed (no user found)")
            return None
                
        except Exception as e:
            _logger.error(f"GPT API Auth Failed with Exception: {type(e).__name__}: {str(e)}")
            # Log full stack trace if needed, but error is usually clear
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
