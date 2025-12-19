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
        We parse the email body looking for CC project links.
        """
        if custom_values is None:
            custom_values = {}

        # Extract subject as name
        subject = msg_dict.get('subject', 'New ITB')
        custom_values['name'] = subject

        # Try to extract CC URL from body
        body = msg_dict.get('body', '') or ''
        url_match = re.search(r'https?://app\.constructconnect\.com/projects/[^\s"\'<>]+', body)
        if url_match:
            custom_values['cc_source_url'] = url_match.group(0)
            # Extract project ID from URL
            id_match = re.search(r'/projects/(\d+)', url_match.group(0))
            if id_match:
                custom_values['cc_project_id'] = id_match.group(1)

        record = super(CCOpportunity, self).message_new(msg_dict, custom_values)
        
        # Auto-fetch if URL found
        if record.cc_source_url:
            record.action_fetch_cc_data()
        
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
