from odoo import models, api
import requests
import re
import logging
import base64

_logger = logging.getLogger(__name__)


class CCAPI(models.AbstractModel):
    """
    Construct Connect API Client (Curl/Requests based).
    This is a lightweight, session-based HTTP client for fetching CC data.
    """
    _name = 'cc.api'
    _description = 'ConstructConnect API Client'

    @api.model
    def get_instance(self):
        """
        Returns an instance of the API client (self).
        """
        return self

    @api.model
    def _get_credentials(self):
        """
        Retrieves CC credentials from System Parameters.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        email = ICP.get_param('cc_ops.email', default='')
        password = ICP.get_param('cc_ops.password', default='')
        return email, password

    @api.model
    def _get_session(self):
        """
        Creates an authenticated requests.Session for ConstructConnect.
        iSqFt redirects to app.constructconnect.com for auth.
        
        The login flow is:
        1. Go to /enteremail - enter email
        2. Redirects to password page
        3. Submit password
        4. Get session cookies
        """
        email, password = self._get_credentials()
        if not email or not password:
            _logger.warning("CC Credentials not configured. Set cc_ops.email and cc_ops.password in System Parameters.")
            return None

        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })

        _logger.info("Attempting ConstructConnect login...")
        
        try:
            # Step 1: Start at the access URL to set initial cookies
            start_url = "https://app.constructconnect.com/enteremail"
            resp = session.get(start_url, timeout=15)
            _logger.info(f"Enter email page status: {resp.status_code}")

            # Step 2: Submit email (find the form and post)
            email_form_url = "https://app.constructconnect.com/enteremail"
            email_data = {
                'email': email,
                'Email': email,  # Try both cases
            }
            resp = session.post(email_form_url, data=email_data, timeout=15, allow_redirects=True)
            _logger.info(f"Email submit status: {resp.status_code}, URL: {resp.url}")

            # Step 3: Submit password
            # The redirect should take us to a password page
            password_data = {
                'password': password,
                'Password': password,
                'email': email,
                'Email': email,
            }
            # Try common login endpoints
            login_urls = [
                "https://app.constructconnect.com/login",
                "https://app.constructconnect.com/Account/Login",
                "https://auth.constructconnect.com/login",
                resp.url,  # Current page might be the login form
            ]
            
            for login_url in login_urls:
                try:
                    resp = session.post(login_url, data=password_data, timeout=15, allow_redirects=True)
                    _logger.info(f"Login attempt to {login_url}: {resp.status_code}, URL: {resp.url}")
                    
                    # Check if we're logged in (not on a login page)
                    if 'login' not in resp.url.lower() and 'enteremail' not in resp.url.lower():
                        _logger.info("ConstructConnect Login successful!")
                        return session
                except Exception as e:
                    _logger.debug(f"Login attempt failed for {login_url}: {e}")
                    continue

            _logger.error("All ConstructConnect login attempts failed")
            return None

        except Exception as e:
            _logger.error(f"ConstructConnect Session creation failed: {e}")
            return None



    @api.model
    def fetch_project(self, url_or_id, access_code=None):
        """
        Fetches project details from ConstructConnect/iSqFt.
        Returns a dict of project data.
        
        The access URL pattern is:
        https://app.isqft.com/services/Access/GetUserQANAccess?sourceType=2&Id={access_code}&ProjectID={project_id}
        
        This redirects to:
        https://app.constructconnect.com/projects/{project_id}
        """
        session = self._get_session()
        if not session:
            return None

        # Extract project ID from URL if needed
        project_id = url_or_id
        if 'isqft.com' in str(url_or_id) or 'constructconnect.com' in str(url_or_id):
            match = re.search(r'ProjectID[=:](\d+)', url_or_id, re.IGNORECASE)
            if match:
                project_id = match.group(1)
            else:
                match = re.search(r'/projects/(\d+)', url_or_id)
                if match:
                    project_id = match.group(1)

        _logger.info(f"Fetching project {project_id}...")

        # Try to access the project page
        project_urls = [
            f"https://app.constructconnect.com/projects/{project_id}",
            f"https://app.constructconnect.com/api/projects/{project_id}",
            url_or_id,  # Try original URL
        ]
        
        for url in project_urls:
            try:
                _logger.info(f"Trying: {url}")
                resp = session.get(url, timeout=30, allow_redirects=True)
                _logger.info(f"Response: {resp.status_code}, URL: {resp.url}")
                
                if resp.status_code == 200:
                    content_type = resp.headers.get('Content-Type', '')
                    
                    # If JSON, parse it
                    if 'json' in content_type:
                        return resp.json()
                    
                    # If HTML, try to extract data
                    html = resp.text
                    data = self._parse_project_html(html)
                    if data:
                        return data
                        
            except Exception as e:
                _logger.debug(f"Fetch error for {url}: {e}")
                continue

        _logger.warning(f"Could not fetch project {project_id}")
        return None

    @api.model
    def _parse_project_html(self, html):
        """
        Extracts project data from HTML page.
        """
        data = {}
        
        # Try to find project name
        title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
        if title_match:
            data['name'] = title_match.group(1).strip()
        
        # Look for common data patterns in the HTML
        # This will need refinement based on actual page structure
        
        return data if data else None


    @api.model
    def download_documents(self, opportunity):
        """
        Downloads all documents for the given opportunity and attaches them.
        """
        session = self._get_session()
        if not session:
            return False

        project_id = opportunity.cc_project_id
        if not project_id:
            return False

        # API endpoint for documents (needs verification)
        docs_url = f"https://app.constructconnect.com/api/projects/{project_id}/documents"
        
        try:
            resp = session.get(docs_url, timeout=30)
            if resp.status_code != 200:
                _logger.warning(f"CC Docs list failed: {resp.status_code}")
                return False

            docs = resp.json()
            if not isinstance(docs, list):
                docs = docs.get('documents', [])

            for doc in docs:
                doc_id = doc.get('id')
                doc_name = doc.get('name', f'document_{doc_id}.pdf')
                download_url = doc.get('downloadUrl') or f"https://app.constructconnect.com/api/documents/{doc_id}/download"

                try:
                    file_resp = session.get(download_url, timeout=120)
                    if file_resp.status_code == 200:
                        self.env['ir.attachment'].create({
                            'name': doc_name,
                            'type': 'binary',
                            'datas': base64.b64encode(file_resp.content),
                            'res_model': 'cc.opportunity',
                            'res_id': opportunity.id,
                            'mimetype': file_resp.headers.get('Content-Type', 'application/pdf'),
                        })
                        _logger.info(f"Downloaded: {doc_name}")
                except Exception as e:
                    _logger.error(f"Failed to download {doc_name}: {e}")

            return True

        except Exception as e:
            _logger.error(f"CC Docs download error: {e}")
            return False
