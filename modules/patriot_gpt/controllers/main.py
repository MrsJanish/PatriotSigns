from odoo import http
from odoo.http import request, Response
import json
import logging

_logger = logging.getLogger(__name__)

class PatriotGPTController(http.Controller):

    def _authenticate(self):
        """
        Authenticates the request using Odoo's native API Keys.
        Expects 'X-Api-Key' or 'Authorization: Bearer <key>' header.
        Returns the user_id (int) if valid, None otherwise.
        """
        try:
            key = request.httprequest.headers.get('X-Api-Key')
            if not key:
                auth_header = request.httprequest.headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    key = auth_header[7:]
            
            if not key:
                _logger.info("GPT API: Missing API Key")
                return None
            
            # Verify against res.users.apikeys
            # method _check_api_key returns the user_id or raises AccessDenied
            if hasattr(request.env['res.users.apikeys'], '_check_api_key'):
                return request.env['res.users.apikeys']._check_api_key(key)
            else:
                # Fallback implementation if specific version differs slightly, 
                # but _check_api_key is standard in recent versions.
                # If we are here, we might be in trouble, but let's try direct search if hashing allows (unlikely)
                _logger.error("GPT API: _check_api_key method not found on res.users.apikeys")
                return None
                
        except Exception as e:
            _logger.error(f"GPT API Auth Failed: {str(e)}")
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
