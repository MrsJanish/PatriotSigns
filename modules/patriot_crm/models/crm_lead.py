# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    """
    CRM Lead extension for sign project management.
    
    Integrates ConstructConnect bid opportunities with Odoo CRM pipeline.
    Each lead represents a potential sign project from bid intake to award.
    """
    _inherit = 'crm.lead'

    # =========================================================================
    # CONSTRUCTCONNECT INTEGRATION
    # =========================================================================
    cc_project_id = fields.Char(
        string='CC Project ID',
        index=True,
        help='ConstructConnect project identifier'
    )
    cc_access_code = fields.Char(
        string='Access Code',
        help='Access code for document download'
    )
    cc_source_url = fields.Char(
        string='Source URL',
        help='Original URL on ConstructConnect'
    )
    cc_data_json = fields.Text(
        string='CC Raw Data',
        help='JSON data from ConstructConnect API'
    )
    is_cc_opportunity = fields.Boolean(
        string='Is CC Opportunity',
        compute='_compute_is_cc_opportunity',
        store=True,
        help='Indicates this lead came from ConstructConnect'
    )

    # =========================================================================
    # BID INFORMATION
    # =========================================================================
    bid_date = fields.Date(
        string='Bid Date',
        tracking=True,
        help='Due date for bid submission'
    )
    bid_time = fields.Char(
        string='Bid Time',
        help='Time of day bid is due (e.g., "2:00 PM CST")'
    )
    bid_type = fields.Selection([
        ('open', 'Open Bid'),
        ('sealed', 'Sealed Bid'),
        ('negotiated', 'Negotiated'),
        ('invited', 'Invited Only'),
    ], string='Bid Type', default='open', tracking=True)
    
    prebid_date = fields.Datetime(
        string='Pre-Bid Meeting',
        help='Date/time of pre-bid meeting if required'
    )
    prebid_mandatory = fields.Boolean(
        string='Pre-Bid Mandatory',
        default=False
    )
    
    # =========================================================================
    # PROJECT PARTIES (Many2one to res.partner)
    # =========================================================================
    gc_partner_id = fields.Many2one(
        'res.partner',
        string='General Contractor',
        domain="[('is_gc', '=', True)]",
        tracking=True,
        help='General contractor for this project'
    )
    owner_partner_id = fields.Many2one(
        'res.partner',
        string='Owner / Client',
        domain="[('is_owner', '=', True)]",
        tracking=True,
        help='Building owner or client'
    )
    architect_partner_id = fields.Many2one(
        'res.partner',
        string='Architect',
        domain="[('is_architect', '=', True)]",
        help='Architect of record'
    )
    
    # Legacy text fields (for migration, will be deprecated)
    gc_name_legacy = fields.Char(
        string='GC Name (Legacy)',
        help='Deprecated: Use gc_partner_id instead'
    )
    owner_name_legacy = fields.Char(
        string='Owner Name (Legacy)',
        help='Deprecated: Use owner_partner_id instead'
    )
    architect_name_legacy = fields.Char(
        string='Architect Name (Legacy)',
        help='Deprecated: Use architect_partner_id instead'
    )

    # =========================================================================
    # PROJECT DETAILS
    # =========================================================================
    project_alias = fields.Char(
        string='Project Alias',
        help='Short name for internal reference (e.g., "OKC Hospital")'
    )
    project_address = fields.Char(
        string='Project Address'
    )
    project_city = fields.Char(
        string='Project City'
    )
    project_state_id = fields.Many2one(
        'res.country.state',
        string='Project State',
        domain="[('country_id.code', '=', 'US')]"
    )
    project_zip = fields.Char(
        string='Project ZIP'
    )
    
    project_type = fields.Selection([
        ('healthcare', 'Healthcare'),
        ('education', 'Education'),
        ('government', 'Government'),
        ('commercial', 'Commercial'),
        ('retail', 'Retail'),
        ('hospitality', 'Hospitality'),
        ('industrial', 'Industrial'),
        ('residential', 'Multi-Family Residential'),
        ('mixed', 'Mixed Use'),
        ('other', 'Other'),
    ], string='Project Type')
    
    project_scope = fields.Text(
        string='Signage Scope',
        help='Description of signage scope for this project'
    )
    
    # =========================================================================
    # DOCUMENTS
    # =========================================================================
    document_ids = fields.Many2many(
        'ir.attachment',
        'crm_lead_attachment_rel',
        'lead_id',
        'attachment_id',
        string='Project Documents',
        help='Construction documents, specs, addenda'
    )
    document_count = fields.Integer(
        string='Documents',
        compute='_compute_document_count'
    )

    # =========================================================================
    # WORKFLOW TRACKING
    # =========================================================================
    docs_fetched = fields.Boolean(
        string='Documents Fetched',
        default=False,
        help='Documents have been downloaded from CC'
    )
    docs_fetched_date = fields.Datetime(
        string='Docs Fetched Date'
    )
    schedule_extracted = fields.Boolean(
        string='Schedule Extracted',
        default=False,
        help='Sign schedule has been extracted from documents'
    )
    estimate_created = fields.Boolean(
        string='Estimate Created',
        default=False,
        help='Cost estimate has been prepared'
    )
    bid_submitted = fields.Boolean(
        string='Bid Submitted',
        default=False,
        tracking=True
    )
    bid_submitted_date = fields.Date(
        string='Bid Submitted Date'
    )
    bid_amount = fields.Float(
        string='Bid Amount',
        tracking=True
    )
    
    # =========================================================================
    # COMPUTED FIELDS
    # =========================================================================
    
    @api.depends('cc_project_id')
    def _compute_is_cc_opportunity(self):
        for lead in self:
            lead.is_cc_opportunity = bool(lead.cc_project_id)

    def _compute_document_count(self):
        for lead in self:
            lead.document_count = len(lead.document_ids)

    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def action_view_sign_types(self):
        """Open sign types for this project"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Sign Types - {self.name}',
            'res_model': 'ps.sign.type',
            'view_mode': 'tree,form',
            'domain': [('opportunity_id', '=', self.id)],
            'context': {'default_opportunity_id': self.id},
        }

    def action_view_documents(self):
        """Open project documents"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Documents - {self.name}',
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,tree,form',
            'domain': [('id', 'in', self.document_ids.ids)],
        }

    def action_open_sign_tally(self):
        """Open the Sign Tally interface"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'cc_ops_sign_tally',
            'params': {
                'opportunityId': self.id,
            },
        }

    def action_open_pdf_viewer(self):
        """Open PDF viewer for this project's documents"""
        self.ensure_one()
        pdf_docs = self.document_ids.filtered(lambda d: d.mimetype == 'application/pdf')
        if pdf_docs:
            return {
                'type': 'ir.actions.client',
                'tag': 'cc_ops_pdf_viewer',
                'params': {
                    'opportunityId': self.id,
                    'attachmentId': pdf_docs[0].id,
                },
            }
        return {'type': 'ir.actions.act_window_close'}

    # =========================================================================
    # PARTNER AUTO-CREATION
    # =========================================================================
    
    def _get_or_create_partner(self, name, partner_type='gc'):
        """
        Find or create a partner by name.
        
        Args:
            name: Company name to search for
            partner_type: 'gc', 'owner', 'architect', or 'supplier'
        
        Returns:
            res.partner record
        """
        if not name:
            return False
        
        Partner = self.env['res.partner']
        
        # Search for existing partner
        partner = Partner.search([
            ('name', 'ilike', name.strip()),
            ('is_company', '=', True),
        ], limit=1)
        
        if not partner:
            # Create new partner with appropriate flags
            vals = {
                'name': name.strip(),
                'is_company': True,
                'company_type': 'company',
            }
            
            if partner_type == 'gc':
                vals['is_gc'] = True
            elif partner_type == 'owner':
                vals['is_owner'] = True
            elif partner_type == 'architect':
                vals['is_architect'] = True
            elif partner_type == 'supplier':
                vals['is_sign_supplier'] = True
            
            partner = Partner.create(vals)
            _logger.info(f"Created new {partner_type} partner: {name}")
        
        return partner

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-link partners from legacy text fields"""
        for vals in vals_list:
            # Auto-create/link GC partner
            if vals.get('gc_name_legacy') and not vals.get('gc_partner_id'):
                partner = self._get_or_create_partner(vals['gc_name_legacy'], 'gc')
                if partner:
                    vals['gc_partner_id'] = partner.id
            
            # Auto-create/link Owner partner
            if vals.get('owner_name_legacy') and not vals.get('owner_partner_id'):
                partner = self._get_or_create_partner(vals['owner_name_legacy'], 'owner')
                if partner:
                    vals['owner_partner_id'] = partner.id
            
            # Auto-create/link Architect partner
            if vals.get('architect_name_legacy') and not vals.get('architect_partner_id'):
                partner = self._get_or_create_partner(vals['architect_name_legacy'], 'architect')
                if partner:
                    vals['architect_partner_id'] = partner.id
        
        return super().create(vals_list)
