# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import re

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

    # NOTE: sign_type_ids, sign_type_count, total_sign_quantity are defined
    # in patriot_signage/models/crm_lead.py because ps.sign.type is in that module

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
    
    # =========================================================================
    # EQUIPMENT RENTAL
    # =========================================================================
    equipment_rental_required = fields.Boolean(
        string='Equipment Rental Required',
        default=False,
        help='Check if rental equipment (lift, scaffold, etc.) is needed'
    )
    equipment_type = fields.Selection([
        ('lift', 'Lift / Boom'),
        ('scaffold', 'Scaffolding'),
        ('forklift', 'Forklift'),
        ('ladder', 'Extension Ladder'),
        ('other', 'Other'),
    ], string='Equipment Type')
    equipment_rental_cost = fields.Float(
        string='Equipment Rental Cost',
        help='Estimated rental cost to pass through to customer'
    )
    equipment_notes = fields.Text(
        string='Equipment Notes'
    )
    
    # =========================================================================
    # INSTALLER BILLING RATES
    # =========================================================================
    installer_choice = fields.Selection([
        ('robert', 'Robert Scott Only'),
        ('bryson', 'Bryson Only'),
        ('both', 'Both (Robert + Bryson)'),
    ], string='Installers', default='both')
    installer_hourly_rate = fields.Float(
        string='Install Hourly Rate',
        compute='_compute_installer_rate',
        store=True,
        help='Hourly rate based on installer selection'
    )
    install_labor_cost = fields.Float(
        string='Install Labor Cost',
        compute='_compute_install_labor_cost',
        store=True,
        help='Est. Install Hours × Hourly Rate'
    )
    total_install_cost = fields.Float(
        string='Total Install Cost',
        compute='_compute_total_install_cost',
        store=True,
        help='Labor + Travel + Equipment'
    )
    
    @api.depends('installer_choice')
    def _compute_installer_rate(self):
        for lead in self:
            if lead.installer_choice == 'robert':
                lead.installer_hourly_rate = 25.0
            elif lead.installer_choice == 'bryson':
                lead.installer_hourly_rate = 15.0
            else:  # both
                lead.installer_hourly_rate = 40.0
    
    @api.depends('estimated_install_hours', 'installer_hourly_rate')
    def _compute_install_labor_cost(self):
        for lead in self:
            lead.install_labor_cost = (lead.estimated_install_hours or 0) * (lead.installer_hourly_rate or 40.0)
    
    @api.depends('install_labor_cost', 'travel_cost', 'equipment_rental_cost')
    def _compute_total_install_cost(self):
        for lead in self:
            lead.total_install_cost = (lead.install_labor_cost or 0) + \
                                       (lead.travel_cost or 0) + \
                                       (lead.equipment_rental_cost or 0)
    
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
        
        leads = super().create(vals_list)
        
        # Trigger project creation if lead is created directly in Reviewing stage
        reviewing_stage = self.env.ref('patriot_crm.stage_reviewing', raise_if_not_found=False)
        if reviewing_stage:
            for lead in leads:
                if lead.stage_id.id == reviewing_stage.id:
                    lead._ensure_project_created()
        
        return leads

    # =========================================================================
    # WORKFLOW AUTOMATIONS
    # =========================================================================
    
    def write(self, vals):
        """
        Override write to trigger actions on stage changes.
        """
        res = super(CrmLead, self).write(vals)
        
        if 'stage_id' in vals:
            # Check if moved to Reviewing stage
            reviewing_stage = self.env.ref('patriot_crm.stage_reviewing', raise_if_not_found=False)
            if reviewing_stage and vals['stage_id'] == reviewing_stage.id:
                for lead in self:
                    lead._ensure_project_created()
                    
        return res

    def action_set_won_rainbowman(self):
        """
        Override Won action to ensure project exists (fallback).
        """
        result = super().action_set_won_rainbowman()
        
        for lead in self:
            lead._ensure_project_created()
        
        return result

    def _ensure_project_created(self):
        """Create project and related records if they don't exist"""
        self.ensure_one()
        
        # Check if project already exists
        Project = self.env['project.project']
        existing = Project.search([('opportunity_id', '=', self.id)], limit=1)
        if existing:
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

    # =========================================================================
    # EMAIL INGESTION (Migrated from cc.opportunity)
    # =========================================================================
    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """
        Called when an email is received that creates a new record.
        Parses iSqFt ITB email format to extract project details.
        
        Merged from cc.opportunity - now goes directly to CRM pipeline.
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
        url_match = re.search(r'https?://app\.isqft\.com/services/Access/GetUserQANAccess[^"\'\<\>\s]+', body)
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
            parts = location.split(',')
            if len(parts) >= 2:
                custom_values['project_address'] = parts[0].strip()
                if len(parts) >= 3:
                    last = parts[-1].strip()
                    state_zip = last.split()
                    if len(state_zip) >= 2:
                        custom_values['project_zip'] = state_zip[-1]
                    custom_values['project_city'] = parts[1].strip()

        # General Contractor (From: field in email)
        gc_match = re.search(r'From:</p>.*?<p[^>]*>([^<]+)</p>', body, re.DOTALL | re.IGNORECASE)
        if gc_match:
            custom_values['gc_name_legacy'] = gc_match.group(1).strip()

        custom_values['type'] = 'opportunity'
        
        # Auto-assign to Tiffany for bidding stage
        tiffany = self.env.ref('patriot_base.employee_tiffany_janish', raise_if_not_found=False)
        if tiffany and tiffany.user_id:
            custom_values['user_id'] = tiffany.user_id.id
        
        record = super(CrmLead, self).message_new(msg_dict, custom_values)
        
        _logger.info(f"Created CRM Lead from ITB email: {record.name}")
        
        # Auto-trigger GitHub Action if we have a CC Project ID
        if record.cc_project_id:
            record.trigger_github_fetch()
        
        return record

    def trigger_github_fetch(self):
        """
        Triggers GitHub Actions workflow to fetch documents.
        Migrated from cc.opportunity.
        """
        self.ensure_one()
        if not self.cc_project_id:
            _logger.warning("No CC Project ID, cannot trigger fetch")
            return
        
        import requests
        
        # Get GitHub token from config
        github_token = self.env['ir.config_parameter'].sudo().get_param('cc_ops.github_token', '')
        if not github_token:
            _logger.warning("GitHub token not configured. Set 'cc_ops.github_token' in System Parameters.")
            self.message_post(body="GitHub token not configured. Cannot auto-fetch documents.")
            return
        
        # Trigger GitHub Actions workflow
        repo = "MrsJanish/PatriotSigns"
        workflow = "fetch_cc_docs.yml"
        url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/dispatches"
        
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        
        data = {
            "ref": "master",
            "inputs": {
                "project_id": str(self.cc_project_id),
                "lead_id": str(self.id),  # Changed from opportunity_id
                "source_url": self.cc_source_url or "",
            }
        }
        
        try:
            # Update stage to Reviewing (default flow)
            # stage_fetching = self.env.ref('patriot_crm.stage_fetching_docs', raise_if_not_found=False)
            # if stage_fetching:
            #     self.stage_id = stage_fetching.id
            
            # Ensure we are in Reviewing stage if not already
            stage_reviewing = self.env.ref('patriot_crm.stage_reviewing', raise_if_not_found=False)
            if stage_reviewing:
                self.stage_id = stage_reviewing.id
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code == 204:
                _logger.info(f"GitHub Action triggered for project {self.cc_project_id}")
                self.message_post(body="Document fetch started via GitHub Actions...")
                self.docs_fetched = False
            else:
                _logger.error(f"GitHub API error: {response.status_code} - {response.text}")
                self.message_post(body=f"Failed to trigger document fetch: {response.status_code}")
        except Exception as e:
            _logger.error(f"Error triggering GitHub Action: {e}")
            self.message_post(body=f"Error triggering fetch: {e}")

    @api.model
    def action_rescue_leads(self):
        """
        One-off cleanup: Move all leads from transient/default stages to 'Reviewing'.
        This allows us to safely delete the unwanted stages without losing leads.
        """
        # Stages to clear out
        unwanted_stages = [
            'New', 'Qualified', 'Proposition', 'Won',  # Default Odoo
            '📧 New ITB', '📥 Fetching Docs'            # Custom Transient
        ]
        
        # Find the destination stage (Reviewing)
        reviewing_stage = self.env.ref('patriot_crm.stage_reviewing', raise_if_not_found=False)
        if not reviewing_stage:
            # Fallback search if XML ID failed
            reviewing_stage = self.env['crm.stage'].search([('name', 'ilike', 'Reviewing')], limit=1)
            
        if not reviewing_stage:
            _logger.error("Cannot rescue leads: 'Reviewing' stage not found!")
            return
            
        # Find leads in unwanted stages
        domain = [('stage_id.name', 'in', unwanted_stages)]
        leads_to_move = self.search(domain)
        
        if leads_to_move:
            _logger.info(f"Rescuing {len(leads_to_move)} leads from unwanted stages to '{reviewing_stage.name}'")
            leads_to_move.write({'stage_id': reviewing_stage.id})
            
            # Post message on leads
            for lead in leads_to_move:
                lead.message_post(body="System: Automatically moved to 'Reviewing' as part of pipeline cleanup.")

    def action_export_sign_schedule(self):
        """
        Exports sign types to an Excel sign schedule.
        Migrated from cc.opportunity.
        """
        self.ensure_one()
        import io
        import base64
        
        try:
            import xlsxwriter
        except ImportError:
            self.message_post(body="xlsxwriter not installed. Please install it to export schedules.")
            return {'type': 'ir.actions.act_window_close'}
        
        # Get sign types for this lead
        sign_types = self.env['ps.sign.type'].search([('opportunity_id', '=', self.id)])
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Sign Schedule')
        
        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#1e293b',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
        })
        cell_format = workbook.add_format({'border': 1, 'align': 'left'})
        
        # Headers
        headers = ['Sign Type', 'Quantity', 'Dimensions', 'Material', 'Mounting', 'Category', 'Status']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Data rows
        for row, st in enumerate(sign_types, start=1):
            worksheet.write(row, 0, st.name or '', cell_format)
            worksheet.write(row, 1, st.quantity or 0, cell_format)
            worksheet.write(row, 2, st.dimensions_display or '', cell_format)
            worksheet.write(row, 3, st.material or '', cell_format)
            worksheet.write(row, 4, st.mounting or '', cell_format)
            worksheet.write(row, 5, st.category_id.name if st.category_id else '', cell_format)
            worksheet.write(row, 6, st.state or '', cell_format)
        
        # Column widths
        for col in range(len(headers)):
            worksheet.set_column(col, col, 15)
        
        workbook.close()
        
        # Create attachment
        file_data = base64.b64encode(output.getvalue())
        filename = f"Sign_Schedule_{self.name or 'Export'}_{fields.Date.today()}.xlsx".replace(' ', '_')
        
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': file_data,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_mark_lost_archive(self):
        """Mark opportunity as lost and archive it"""
        self.ensure_one()
        self.action_set_lost()
        self.active = False
        return {'type': 'ir.actions.act_window_close'}

