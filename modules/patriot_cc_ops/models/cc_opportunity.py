from odoo import models, fields, api
import re
import logging

_logger = logging.getLogger(__name__)


class CCOpportunity(models.Model):
    _name = 'cc.opportunity'
    _description = 'Construct Connect Opportunity'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'bid_date asc, id desc'

    # --- CORE FIELDS ---
    name = fields.Char(string="Project Name", required=True, tracking=True)
    active = fields.Boolean(default=True)
    
    state = fields.Selection([
        ('new', 'New'),
        ('fetching', 'Fetching Data...'),
        ('ready', 'Ready'),
        ('bidding', 'Bidding'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    ], default='new', string="Status", tracking=True)

    # --- CC DATA ---
    cc_project_id = fields.Char(string="CC Project ID", readonly=True)
    cc_access_code = fields.Char(string="Access Code", readonly=True)
    cc_source_url = fields.Char(string="Source URL")

    
    # --- PROJECT INFO ---
    project_number = fields.Char(string="Project #")
    bid_date = fields.Date(string="Bid Date", tracking=True)
    bid_time = fields.Char(string="Bid Time")
    
    project_type = fields.Char(string="Project Type")
    project_stage = fields.Char(string="Stage")
    estimated_value = fields.Float(string="Est. Value ($)")
    
    # --- LOCATION ---
    street = fields.Char(string="Street")
    city = fields.Char(string="City")
    state_id = fields.Char(string="State")  # Simplified; could be Many2one to res.country.state
    zip_code = fields.Char(string="ZIP")
    county = fields.Char(string="County")
    
    # --- CONTACTS ---
    owner_name = fields.Char(string="Owner")
    architect_name = fields.Char(string="Architect")
    gc_name = fields.Char(string="General Contractor")

    # --- DOCUMENTS ---
    document_ids = fields.One2many('ir.attachment', 'res_id', 
        domain=[('res_model', '=', 'cc.opportunity')],
        string="Construction Documents")
    document_count = fields.Integer(compute='_compute_document_count', string="# Docs")

    # --- EMAIL PARSING ---
    source_email_id = fields.Many2one('mail.message', string="Source Email")

    @api.depends('document_ids')
    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    # --- EMAIL INGESTION ---
    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """
        Called when an email is received that creates a new record.
        Parses iSqFt ITB email format to extract project details.
        """
        if custom_values is None:
            custom_values = {}

        subject = msg_dict.get('subject', 'New ITB')
        body = msg_dict.get('body', '') or ''
        
        # --- PARSE iSqFt EMAIL FORMAT ---
        
        # Project Name (from "You have been invited to bid:" section)
        project_name = subject.replace('Invitation to Bid -', '').replace(': Main Trades', '').strip()
        name_match = re.search(r'You have been invited to bid:</p>\s*</td>\s*</tr>\s*<tr>.*?<p[^>]*>([^<]+)</p>', body, re.DOTALL | re.IGNORECASE)
        if name_match:
            project_name = name_match.group(1).strip()
        custom_values['name'] = f"ITB: {project_name}"

        # Access URL and Project ID
        url_match = re.search(r'https?://app\.isqft\.com/services/Access/GetUserQANAccess[^"\'<>\s]+', body)
        if url_match:
            custom_values['cc_source_url'] = url_match.group(0).replace('&amp;', '&')
        
        id_match = re.search(r'ProjectID[=:](\d+)', body, re.IGNORECASE)
        if id_match:
            custom_values['cc_project_id'] = id_match.group(1)
        
        access_match = re.search(r'Id[=:]([A-Z0-9]+)', body, re.IGNORECASE)
        if access_match:
            custom_values['cc_access_code'] = access_match.group(1)

        # Bid Date
        bid_match = re.search(r'Bid Due Date:</p>.*?<p[^>]*>([^<]+)</p>', body, re.DOTALL | re.IGNORECASE)
        if bid_match:
            bid_str = bid_match.group(1).strip()
            custom_values['bid_time'] = bid_str
            # Try to parse date
            date_match = re.search(r'(\w+),\s+(\w+)\s+(\d+),\s+(\d{4})', bid_str)
            if date_match:
                from datetime import datetime
                try:
                    month_str = date_match.group(2)
                    day = int(date_match.group(3))
                    year = int(date_match.group(4))
                    months = {'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
                              'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12}
                    month = months.get(month_str, 1)
                    custom_values['bid_date'] = f"{year}-{month:02d}-{day:02d}"
                except:
                    pass

        # Location
        loc_match = re.search(r'Project Location:</p>.*?<p[^>]*>([^<]+)</p>', body, re.DOTALL | re.IGNORECASE)
        if loc_match:
            location = loc_match.group(1).strip()
            # Parse "840 Asp Ave, Norman, OK 73069"
            parts = location.split(',')
            if len(parts) >= 2:
                custom_values['street'] = parts[0].strip()
                city_state = parts[1].strip() if len(parts) == 2 else parts[1].strip()
                # Last part might have state and zip
                if len(parts) >= 3:
                    last = parts[-1].strip()
                    state_zip = last.split()
                    if len(state_zip) >= 2:
                        custom_values['state_id'] = state_zip[0]
                        custom_values['zip_code'] = state_zip[1]
                    custom_values['city'] = parts[1].strip()

        # General Contractor (From: field in email)
        gc_match = re.search(r'From:</p>.*?<p[^>]*>([^<]+)</p>', body, re.DOTALL | re.IGNORECASE)
        if gc_match:
            custom_values['gc_name'] = gc_match.group(1).strip()

        # GC Contact
        contact_match = re.search(r'Contact:</p>.*?<p[^>]*>([^<]+)</p>', body, re.DOTALL | re.IGNORECASE)
        if contact_match:
            custom_values['architect_name'] = contact_match.group(1).strip()  # Using architect field for contact

        # Description
        desc_match = re.search(r'Description:</p>.*?<p[^>]*>(.*?)</p>', body, re.DOTALL | re.IGNORECASE)
        if desc_match:
            desc = re.sub(r'<[^>]+>', ' ', desc_match.group(1))  # Strip HTML tags
            desc = re.sub(r'\s+', ' ', desc).strip()
            # Store in a field... we don't have one, use owner for now or add note
            custom_values['owner_name'] = desc[:200] if len(desc) > 200 else desc
        
        custom_values['state'] = 'new'
        
        record = super(CCOpportunity, self).message_new(msg_dict, custom_values)
        
        _logger.info(f"Created CC Opportunity from email: {record.name}")
        
        return record


    def action_fetch_cc_data(self):
        """
        Fetches project details from ConstructConnect using API/Requests.
        """
        self.ensure_one()
        self.state = 'fetching'
        
        try:
            api = self.env['cc.api'].get_instance()
            data = api.fetch_project(self.cc_source_url or self.cc_project_id)
            
            if data:
                self.write({
                    'name': data.get('name', self.name),
                    'project_number': data.get('projectNumber'),
                    'bid_date': data.get('bidDate'),
                    'bid_time': data.get('bidTime'),
                    'project_type': data.get('projectType'),
                    'project_stage': data.get('stage'),
                    'estimated_value': data.get('estimatedValue'),
                    'street': data.get('address', {}).get('street'),
                    'city': data.get('address', {}).get('city'),
                    'state_id': data.get('address', {}).get('state'),
                    'zip_code': data.get('address', {}).get('zip'),
                    'county': data.get('address', {}).get('county'),
                    'owner_name': data.get('owner'),
                    'architect_name': data.get('architect'),
                    'gc_name': data.get('generalContractor'),
                    'state': 'ready',
                })
                
                # Fetch Documents
                api.download_documents(self)
                
                _logger.info(f"CC Data fetched for {self.name}")
            else:
                self.state = 'new'
                self.message_post(body="Failed to fetch data from ConstructConnect.")
                
        except Exception as e:
            _logger.error(f"Error fetching CC data: {e}")
            self.state = 'new'
            self.message_post(body=f"Error: {e}")
    
    def action_view_documents(self):
        """
        Opens the document viewer.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Construction Documents',
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,list,form',
            'domain': [('res_model', '=', 'cc.opportunity'), ('res_id', '=', self.id)],
            'context': {'default_res_model': 'cc.opportunity', 'default_res_id': self.id},
        }
