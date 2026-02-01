from odoo import http
from odoo.http import request, Response
import json
import logging

_logger = logging.getLogger(__name__)


class AISearchController(http.Controller):
    """AI-powered task/project search using OpenAI."""

    @http.route('/timeclock/ai-search', type='json', auth='user', methods=['POST'])
    def ai_search(self, query, **kwargs):
        """
        Search for projects/tasks using AI natural language matching.
        
        Args:
            query: Natural language search string (e.g., "hospital signage", "that fab job")
            
        Returns:
            List of 1-3 matches with confidence scores
        """
        if not query or len(query.strip()) < 2:
            return {'results': [], 'error': 'Query too short'}
        
        try:
            # Get OpenAI API key from system parameters
            api_key = request.env['ir.config_parameter'].sudo().get_param('openai.api_key')
            if not api_key:
                _logger.warning("OpenAI API key not configured")
                return self._fallback_search(query)
            
            # Get user's projects and tasks
            user = request.env.user
            employee = request.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
            
            # Fetch active projects
            projects = request.env['project.project'].search_read(
                [('active', '=', True)],
                ['id', 'name'],
                limit=50
            )
            
            # Fetch user's assigned tasks
            tasks = request.env['project.task'].search_read(
                [
                    ('user_ids', 'in', [user.id]),
                    ('is_closed', '=', False),
                ],
                ['id', 'name', 'project_id'],
                limit=50
            )
            
            # Build context for AI
            items = []
            for p in projects:
                items.append(f"PROJECT:{p['id']}:{p['name']}")
            for t in tasks:
                project_name = t['project_id'][1] if t['project_id'] else 'No Project'
                items.append(f"TASK:{t['id']}:{t['name']} ({project_name})")
            
            if not items:
                return {'results': [], 'message': 'No projects or tasks found'}
            
            # Call OpenAI
            import requests as req
            
            prompt = f"""You are helping a sign shop employee find what they want to clock into.

User searched: "{query}"

Available items:
{chr(10).join(items)}

Return a JSON array of matches (1-3 items max). If confident, return 1. If unsure, return up to 3 options.
Format: [{{"type": "PROJECT" or "TASK", "id": number, "name": "display name", "confidence": 0.0-1.0}}]

Only return the JSON array, nothing else."""

            response = req.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'gpt-4o-mini',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.3,
                    'max_tokens': 300
                },
                timeout=10
            )
            
            if response.status_code != 200:
                _logger.error(f"OpenAI API error: {response.text}")
                return self._fallback_search(query)
            
            data = response.json()
            content = data['choices'][0]['message']['content'].strip()
            
            # Parse JSON response
            # Handle markdown code blocks
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            
            matches = json.loads(content)
            
            # Validate and enrich results
            results = []
            for match in matches[:3]:
                if match['type'] == 'PROJECT':
                    project = request.env['project.project'].browse(match['id'])
                    if project.exists():
                        results.append({
                            'type': 'project',
                            'id': project.id,
                            'name': project.name,
                            'display': project.name,
                            'confidence': match.get('confidence', 0.8)
                        })
                elif match['type'] == 'TASK':
                    task = request.env['project.task'].browse(match['id'])
                    if task.exists():
                        results.append({
                            'type': 'task',
                            'id': task.id,
                            'name': task.name,
                            'project_id': task.project_id.id if task.project_id else False,
                            'project_name': task.project_id.name if task.project_id else '',
                            'display': f"{task.project_id.name} → {task.name}" if task.project_id else task.name,
                            'confidence': match.get('confidence', 0.8)
                        })
            
            return {'results': results}
            
        except Exception as e:
            _logger.exception("AI Search error")
            return self._fallback_search(query)
    
    def _fallback_search(self, query):
        """Fallback to simple text search if AI fails."""
        query_lower = query.lower()
        results = []
        
        # Search tasks first
        tasks = request.env['project.task'].search([
            ('user_ids', 'in', [request.env.user.id]),
            ('is_closed', '=', False),
            '|',
            ('name', 'ilike', query),
            ('project_id.name', 'ilike', query)
        ], limit=3)
        
        for task in tasks:
            results.append({
                'type': 'task',
                'id': task.id,
                'name': task.name,
                'project_id': task.project_id.id if task.project_id else False,
                'project_name': task.project_id.name if task.project_id else '',
                'display': f"{task.project_id.name} → {task.name}" if task.project_id else task.name,
                'confidence': 0.7
            })
        
        # If no tasks, search projects
        if not results:
            projects = request.env['project.project'].search([
                ('name', 'ilike', query),
                ('active', '=', True)
            ], limit=3)
            
            for project in projects:
                results.append({
                    'type': 'project',
                    'id': project.id,
                    'name': project.name,
                    'display': project.name,
                    'confidence': 0.7
                })
        
        return {'results': results, 'fallback': True}
