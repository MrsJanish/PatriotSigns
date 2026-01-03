# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Project(models.Model):
    """
    Project extension for sign contract management.
    
    When a CRM lead is won, it converts to a project for execution.
    Tracks contracts, insurance, submittals, production, and installation.
    """
    _inherit = 'project.project'
    _rec_names_search = ['name', 'project_alias', 'project_number']  # Search by alias/number too

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=None, order=None):
        """Extended search to find projects by task name."""
        domain = domain or []
        
        # First do the standard search
        project_ids = super()._name_search(name, domain, operator, limit, order)
        
        if name and operator in ('ilike', 'like', '='):
            # Also search for projects that have tasks matching the search term
            tasks = self.env['project.task'].search([
                ('name', operator, name),
                ('project_id', '!=', False)
            ], limit=limit)
            
            if tasks:
                # Get the project IDs from matching tasks
                task_project_ids = tasks.mapped('project_id').ids
                # Combine with original results, removing duplicates
                project_ids = list(dict.fromkeys(list(project_ids) + task_project_ids))
        
        return project_ids[:limit] if limit else project_ids

    # =========================================================================
    # CRM LINK
    # =========================================================================
    opportunity_id = fields.Many2one(
        'crm.lead',
        string='Source Opportunity',
        help='The CRM opportunity that became this project'
    )
    
    # =========================================================================
    # TIME TRACKING
    # =========================================================================
    total_hours = fields.Float(
        string='Total Hours',
        compute='_compute_total_hours',
        store=True
    )
    total_hours_display = fields.Char(
        string='Total Time',
        compute='_compute_total_hours'
    )
    time_punch_ids = fields.One2many(
        'ps.time.punch',
        'project_id',
        string='Time Punches'
    )
    time_punch_count = fields.Integer(
        string='Punch Count',
        compute='_compute_total_hours'
    )
    
    @api.depends('time_punch_ids', 'time_punch_ids.duration_hours')
    def _compute_total_hours(self):
        for project in self:
            punches = project.time_punch_ids.filtered(lambda p: p.state == 'closed')
            total = sum(punches.mapped('duration_hours'))
            project.total_hours = total
            project.time_punch_count = len(project.time_punch_ids)
            
            # Format as Xh Ym
            hours = int(total)
            minutes = int((total - hours) * 60)
            project.total_hours_display = f"{hours}h {minutes}m"
    
    # =========================================================================
    # PROJECT DETAILS
    # =========================================================================
    project_alias = fields.Char(
        string='Project Alias',
        help='Short internal name'
    )
    project_number = fields.Char(
        string='Project Number',
        help='Internal project number'
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
    
    # =========================================================================
    # PROJECT PARTIES
    # =========================================================================
    gc_partner_id = fields.Many2one(
        'res.partner',
        string='General Contractor',
        domain="[('is_gc', '=', True)]"
    )
    owner_partner_id = fields.Many2one(
        'res.partner',
        string='Owner / Client',
        domain="[('is_owner', '=', True)]"
    )
    architect_partner_id = fields.Many2one(
        'res.partner',
        string='Architect',
        domain="[('is_architect', '=', True)]"
    )
    
    # =========================================================================
    # PROJECT LOCATION
    # =========================================================================
    project_address = fields.Char(string='Address')
    project_city = fields.Char(string='City')
    project_state_id = fields.Many2one(
        'res.country.state',
        string='State',
        domain="[('country_id.code', '=', 'US')]"
    )
    project_zip = fields.Char(string='ZIP')

    # =========================================================================
    # CONTRACT
    # =========================================================================
    contract_id = fields.Many2one(
        'ps.contract',
        string='Contract'
    )
    contract_amount = fields.Float(
        string='Contract Amount'
    )
    contract_date = fields.Date(
        string='Contract Date'
    )
    po_number = fields.Char(
        string='PO Number'
    )
    
    # =========================================================================
    # KEY DATES
    # =========================================================================
    award_date = fields.Date(
        string='Award Date'
    )
    submittals_due = fields.Date(
        string='Submittals Due'
    )
    production_start = fields.Date(
        string='Production Start'
    )
    ship_date = fields.Date(
        string='Ship Date'
    )
    install_start = fields.Date(
        string='Install Start'
    )
    install_complete = fields.Date(
        string='Install Complete'
    )
    
    # =========================================================================
    # SIGN SCHEDULE
    # =========================================================================
    sign_type_ids = fields.One2many(
        related='opportunity_id.sign_type_ids',
        string='Sign Types'
    )
    sign_type_count = fields.Integer(
        compute='_compute_sign_counts'
    )
    total_sign_quantity = fields.Integer(
        compute='_compute_sign_counts'
    )
    
    # =========================================================================
    # INSURANCE / COI
    # =========================================================================
    coi_received = fields.Boolean(
        string='COI Received',
        default=False
    )
    coi_expiry = fields.Date(
        string='COI Expiry'
    )
    coi_attachment_id = fields.Many2one(
        'ir.attachment',
        string='COI Document'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    project_stage = fields.Selection([
        ('contract', 'Contract'),
        ('submittals', 'Submittals'),
        ('approved', 'Approved'),
        ('production', 'Production'),
        ('shipping', 'Shipping'),
        ('installation', 'Installation'),
        ('punchlist', 'Punchlist'),
        ('closeout', 'Closeout'),
        ('complete', 'Complete'),
    ], string='Project Stage', default='contract', tracking=True)
    
    # =========================================================================
    # COMPUTED
    # =========================================================================
    
    @api.depends('sign_type_ids')
    def _compute_sign_counts(self):
        for project in self:
            if project.opportunity_id:
                project.sign_type_count = len(project.opportunity_id.sign_type_ids)
                project.total_sign_quantity = sum(project.opportunity_id.sign_type_ids.mapped('quantity'))
            else:
                project.sign_type_count = 0
                project.total_sign_quantity = 0

    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    @api.model
    def create_from_opportunity(self, opportunity):
        """Create project from won CRM opportunity.
        
        If a [Bid] project already exists for this opportunity (from pre-bid time logging),
        we reuse it and update it with the full project details.
        """
        # Check if there's already a project for this opportunity (from pre-bid time logging)
        existing_project = self.search([('opportunity_id', '=', opportunity.id)], limit=1)
        
        project_vals = {
            'name': opportunity.name,  # Remove [Bid] prefix if it was there
            'opportunity_id': opportunity.id,
            'project_alias': opportunity.project_alias,
            'gc_partner_id': opportunity.gc_partner_id.id if opportunity.gc_partner_id else False,
            'owner_partner_id': opportunity.owner_partner_id.id if opportunity.owner_partner_id else False,
            'architect_partner_id': opportunity.architect_partner_id.id if opportunity.architect_partner_id else False,
            'project_address': opportunity.project_address,
            'project_city': opportunity.project_city,
            'project_state_id': opportunity.project_state_id.id if opportunity.project_state_id else False,
            'project_zip': opportunity.project_zip,
            'project_type': opportunity.project_type,
            'award_date': fields.Date.today(),
            'project_stage': 'contract',
            'allow_timesheets': True,
        }
        
        if existing_project:
            # Update the existing [Bid] project with full details
            existing_project.write(project_vals)
            project = existing_project
        else:
            # No existing project - create from template if available
            template = self.env.ref('patriot_projects.project_project_signage_template', raise_if_not_found=False)
            
            if template:
                project = template.copy(default=project_vals)
                project.active = True
            else:
                project = self.create(project_vals)

        # Ensure a "General" task exists for high-level time logging
        Task = self.env['project.task']
        if not Task.search_count([('project_id', '=', project.id), ('name', 'ilike', 'General')]):
            Task.create({
                'name': 'General - Project Time',
                'project_id': project.id,
                'description': 'Log general project hours here if not in a specific phase.',
            })
        
        # Transfer any pre-bid time punches from the opportunity to this project
        TimePunch = self.env['ps.time.punch']
        opportunity_punches = TimePunch.search([('opportunity_id', '=', opportunity.id)])
        if opportunity_punches:
            opportunity_punches.write({
                'project_id': project.id,
                'opportunity_id': False,  # Clear the opportunity link
            })

        return project

    def action_view_sign_types(self):
        """View sign types for this project"""
        self.ensure_one()
        if self.opportunity_id:
            return self.opportunity_id.action_view_sign_types()
        return {'type': 'ir.actions.act_window_close'}
