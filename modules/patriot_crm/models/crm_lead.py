# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
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
    # MILEAGE & TRAVEL TRACKING
    # =========================================================================
    shop_address = fields.Char(
        string='Shop Address',
        default='1234 Industrial Blvd, Oklahoma City, OK 73108',
        help='Starting address for distance calculation'
    )
    distance_miles = fields.Float(
        string='Distance (Miles)',
        help='One-way distance from shop to project site'
    )
    mileage_rate = fields.Float(
        string='Mileage Rate ($/mile)',
        default=0.67,
        help='IRS standard mileage rate or custom rate'
    )
    travel_cost = fields.Float(
        string='Travel Cost',
        compute='_compute_travel_cost',
        store=True,
        help='Round-trip travel cost (distance × 2 × rate)'
    )
    estimated_install_hours = fields.Float(
        string='Est. Install Hours',
        help='Estimated hours for installation'
    )
    
    @api.depends('distance_miles', 'mileage_rate')
    def _compute_travel_cost(self):
        for lead in self:
            # Round trip calculation
            lead.travel_cost = (lead.distance_miles or 0) * 2 * (lead.mileage_rate or 0.67)
    
    def action_calculate_distance(self):
        """Calculate distance from shop to project using Google Maps API"""
        import requests
        
        self.ensure_one()
        
        # Get API key from system parameters
        api_key = self.env['ir.config_parameter'].sudo().get_param('google_maps_api_key', '')
        
        if not api_key:
            raise UserError("Google Maps API key not configured. Go to Settings > Technical > Parameters > System Parameters and add 'google_maps_api_key'")
        
        # Build origin address (shop location)
        origin = self.shop_address or '1234 Industrial Blvd, Oklahoma City, OK 73108'
        
        # Build destination from project address fields
        dest_parts = [
            self.project_address or '',
            self.project_city or '',
            self.project_state_id.name if self.project_state_id else '',
            self.project_zip or ''
        ]
        destination = ', '.join([p for p in dest_parts if p])
        
        if not destination:
            raise UserError("Please enter the project address first.")
        
        # Call Google Distance Matrix API
        url = 'https://maps.googleapis.com/maps/api/distancematrix/json'
        params = {
            'origins': origin,
            'destinations': destination,
            'units': 'imperial',  # Get miles
            'key': api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('status') == 'OK':
                element = data['rows'][0]['elements'][0]
                if element.get('status') == 'OK':
                    # Distance is returned in meters, convert to miles
                    distance_meters = element['distance']['value']
                    distance_miles = distance_meters * 0.000621371
                    self.distance_miles = round(distance_miles, 1)
                else:
                    raise UserError(f"Could not calculate distance: {element.get('status')}")
            else:
                raise UserError(f"Google Maps API error: {data.get('status')}")
                
        except requests.RequestException as e:
            raise UserError(f"Network error calling Google Maps: {str(e)}")
    
    @api.onchange('project_zip')
    def _onchange_project_zip(self):
        """Auto-calculate distance when ZIP is entered"""
        if self.project_zip and len(self.project_zip) >= 5:
            try:
                self.action_calculate_distance()
            except Exception:
                # Silently fail - user can manually trigger if needed
                pass
    
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
            'view_mode': 'list,form',
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

    # =========================================================================
    # WORKFLOW AUTOMATIONS
    # =========================================================================
    
    def action_set_won_rainbowman(self):
        """
        Override Won action to trigger project creation workflow.
        
        When opportunity is marked as Won:
        1. Create a Project record
        2. Create initial Submittal record
        3. Copy over sign types and project data
        """
        # Call parent method first
        result = super().action_set_won_rainbowman()
        
        # Trigger project creation for each won opportunity
        for lead in self:
            lead._create_project_from_won()
        
        return result

    def _create_project_from_won(self):
        """Create project and related records when opportunity is won"""
        self.ensure_one()
        
        # Check if project already exists
        Project = self.env['project.project']
        existing = Project.search([('opportunity_id', '=', self.id)], limit=1)
        if existing:
            _logger.info(f"Project already exists for opportunity {self.name}")
            return existing
        
        # Create the project
        project = Project.create_from_opportunity(self)
        _logger.info(f"Created project {project.name} from opportunity {self.name}")
        
        # Create initial submittal
        self._create_initial_submittal(project)
        
        # Create production order placeholder
        self._create_production_order(project)
        
        return project

    def _create_initial_submittal(self, project):
        """Create the initial shop drawing submittal for a new project"""
        Submittal = self.env.get('ps.submittal')
        if not Submittal:
            return False
        
        # Get sign types from this opportunity
        sign_types = self.env['ps.sign.type'].search([
            ('opportunity_id', '=', self.id)
        ])
        
        submittal = Submittal.create({
            'name': f"{project.name} - Shop Drawings",
            'project_id': project.id,
            'submittal_type': 'shop',
            'spec_section': '10 14 00',
            'spec_title': 'Interior Signage',
            'sign_type_ids': [(6, 0, sign_types.ids)] if sign_types else [],
            'state': 'draft',
        })
        _logger.info(f"Created submittal {submittal.name} for project {project.name}")
        return submittal

    def _create_production_order(self, project):
        """Create a production order placeholder for the project"""
        ProductionOrder = self.env.get('ps.production.order')
        if not ProductionOrder:
            return False
        
        production = ProductionOrder.create({
            'name': f"PO-{project.name}",
            'project_id': project.id,
            'opportunity_id': self.id,
            'state': 'draft',
        })
        _logger.info(f"Created production order {production.name} for project {project.name}")
        return production
