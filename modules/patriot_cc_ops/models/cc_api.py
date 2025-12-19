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
        Creates an authenticated requests.Session for iSqFt/ConstructConnect.
        Uses cookie-based session auth (like a browser).
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

        _logger.info("Attempting iSqFt login...")
        
        try:
            # Step 1: Get login page (for cookies/tokens)
            login_page = session.get("https://app.isqft.com/Account/Login", timeout=15)
            _logger.info(f"Login page status: {login_page.status_code}")

            # Step 2: Form-based login
            form_data = {
                'Email': email,
                'Password': password,
                'RememberMe': 'true'
            }
            resp = session.post(
                "https://app.isqft.com/Account/Login",
                data=form_data,
                timeout=30,
                allow_redirects=True
            )
            _logger.info(f"Login POST status: {resp.status_code}, URL: {resp.url}")

            # Check if we're logged in (not on login page)
            if 'login' not in resp.url.lower() and resp.status_code == 200:
                _logger.info("iSqFt Login successful!")
                return session
            else:
                _logger.error("iSqFt Login failed - still on login page")
                return None

        except Exception as e:
            _logger.error(f"iSqFt Session creation failed: {e}")
            return None


    @api.model
    def fetch_project(self, url_or_id):
        """
        Fetches project details from ConstructConnect.
        Returns a dict of project data.
        """
        session = self._get_session()
        if not session:
            return None

        # Extract project ID from URL if needed
        project_id = url_or_id
        if 'constructconnect.com' in str(url_or_id):
            match = re.search(r'/projects/(\d+)', url_or_id)
            if match:
                project_id = match.group(1)

        # API endpoint (needs verification)
        api_url = f"https://app.constructconnect.com/api/projects/{project_id}"
        
        try:
            resp = session.get(api_url, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            else:
                _logger.warning(f"CC Project fetch failed: {resp.status_code}")
                return None
        except Exception as e:
            _logger.error(f"CC Fetch error: {e}")
            return None

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
