# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Installation(models.Model):
    """
    Installation - Sign installation job.
    
    Represents a single installation visit or trip.
    Links to project, crew, and sign instances being installed.
    """
    _name = 'ps.installation'
    _description = 'Installation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_date desc'

    # =========================================================================
    # IDENTIFICATION
    # =========================================================================
    name = fields.Char(
        string='Installation #',
        required=True,
        tracking=True
    )
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        ondelete='cascade'
    )
    
    # =========================================================================
    # SCHEDULING
    # =========================================================================
    scheduled_date = fields.Date(
        string='Scheduled Date',
        required=True,
        tracking=True
    )
    scheduled_time = fields.Char(
        string='Scheduled Time',
        help='e.g., "8:00 AM", "Morning"'
    )
    duration_estimate = fields.Float(
        string='Est. Duration (hrs)',
        default=8.0
    )
    
    actual_start = fields.Datetime(
        string='Actual Start'
    )
    actual_end = fields.Datetime(
        string='Actual End'
    )
    actual_duration = fields.Float(
        string='Actual Duration',
        compute='_compute_actual_duration',
        store=True
    )
    
    # =========================================================================
    # CREW
    # =========================================================================
    crew_id = fields.Many2one(
        'ps.crew',
        string='Crew',
        tracking=True
    )
    lead_installer_id = fields.Many2one(
        'res.users',
        string='Lead Installer'
    )
    installer_ids = fields.Many2many(
        'res.users',
        'ps_installation_installer_rel',
        'installation_id',
        'user_id',
        string='Installers'
    )
    
    # =========================================================================
    # LOCATION
    # =========================================================================
    location_address = fields.Char(
        related='project_id.project_address',
        string='Address'
    )
    location_city = fields.Char(
        related='project_id.project_city',
        string='City'
    )
    site_contact = fields.Char(
        string='Site Contact'
    )
    site_contact_phone = fields.Char(
        string='Site Phone'
    )
    
    # =========================================================================
    # SIGN INSTANCES
    # =========================================================================
    instance_ids = fields.Many2many(
        'ps.sign.instance',
        'ps_installation_instance_rel',
        'installation_id',
        'instance_id',
        string='Signs to Install'
    )
    instance_count = fields.Integer(
        string='Signs',
        compute='_compute_instance_count'
    )
    installed_count = fields.Integer(
        string='Installed',
        compute='_compute_installed_count'
    )
    
    # =========================================================================
    # REQUIREMENTS
    # =========================================================================
    requires_lift = fields.Boolean(
        string='Requires Lift',
        default=False
    )
    lift_type = fields.Char(
        string='Lift Type'
    )
    requires_scaffold = fields.Boolean(
        string='Requires Scaffold',
        default=False
    )
    special_equipment = fields.Text(
        string='Special Equipment'
    )
    
    # =========================================================================
    # ACCESS
    # =========================================================================
    access_notes = fields.Text(
        string='Access Notes',
        help='Parking, building access, security requirements'
    )
    gc_onsite_contact = fields.Char(
        string='GC Onsite Contact'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('complete', 'Complete'),
        ('partial', 'Partial Install'),
        ('canceled', 'Canceled'),
    ], string='Status', default='scheduled', tracking=True)
    
    # =========================================================================
    # NOTES
    # =========================================================================
    notes = fields.Text(
        string='Installation Notes'
    )
    
    # =========================================================================
    # PUNCHLIST
    # =========================================================================
    punchlist_ids = fields.One2many(
        'ps.punchlist.item',
        'installation_id',
        string='Punchlist Items'
    )
    punchlist_count = fields.Integer(
        string='Punchlist',
        compute='_compute_punchlist_count'
    )
    
    # =========================================================================
    # PHOTOS
    # =========================================================================
    photo_ids = fields.Many2many(
        'ir.attachment',
        'ps_installation_photo_rel',
        'installation_id',
        'attachment_id',
        string='Photos'
    )

    # =========================================================================
    # COMPUTED
    # =========================================================================
    
    @api.depends('actual_start', 'actual_end')
    def _compute_actual_duration(self):
        for install in self:
            if install.actual_start and install.actual_end:
                delta = install.actual_end - install.actual_start
                install.actual_duration = delta.total_seconds() / 3600
            else:
                install.actual_duration = 0

    @api.depends('instance_ids')
    def _compute_instance_count(self):
        for install in self:
            install.instance_count = len(install.instance_ids)

    @api.depends('instance_ids.installed')
    def _compute_installed_count(self):
        for install in self:
            install.installed_count = len(install.instance_ids.filtered('installed'))

    @api.depends('punchlist_ids')
    def _compute_punchlist_count(self):
        for install in self:
            install.punchlist_count = len(install.punchlist_ids)

    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def action_confirm(self):
        """Confirm installation"""
        self.write({'state': 'confirmed'})

    def action_start(self):
        """Start installation"""
        self.write({
            'state': 'in_progress',
            'actual_start': fields.Datetime.now(),
        })

    def action_complete(self):
        """Complete installation and trigger billing"""
        self.write({
            'state': 'complete',
            'actual_end': fields.Datetime.now(),
        })
        # Mark all instances as installed
        self.instance_ids.write({
            'installed': True,
            'installed_date': fields.Date.today(),
            'state': 'installed',
        })
        # Update project stage
        for install in self:
            if install.project_id:
                install.project_id.write({'project_stage': 'punchlist'})
            # Create pay application
            install._create_pay_application()

    def _create_pay_application(self):
        """Create pay application when installation completes"""
        self.ensure_one()
        PayApp = self.env.get('ps.pay.application')
        if not PayApp:
            return False
        
        # Get existing pay apps for this project
        existing = PayApp.search([
            ('project_id', '=', self.project_id.id)
        ], order='application_number desc', limit=1)
        next_number = (existing.application_number + 1) if existing else 1
        
        # Create pay application
        pay_app = PayApp.create({
            'application_number': next_number,
            'project_id': self.project_id.id,
            'period_start': fields.Date.today(),
            'period_end': fields.Date.today(),
            'state': 'draft',
        })
        return pay_app


class PunchlistItem(models.Model):
    """
    Punchlist Item - Issue found during or after installation.
    """
    _name = 'ps.punchlist.item'
    _description = 'Punchlist Item'
    _order = 'installation_id, sequence'

    installation_id = fields.Many2one(
        'ps.installation',
        string='Installation',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    # Item details
    instance_id = fields.Many2one(
        'ps.sign.instance',
        string='Sign Instance'
    )
    issue_type = fields.Selection([
        ('damage', 'Damage'),
        ('wrong', 'Wrong Sign'),
        ('missing', 'Missing'),
        ('alignment', 'Alignment Issue'),
        ('copy', 'Copy Error'),
        ('other', 'Other'),
    ], string='Issue Type', required=True)
    
    description = fields.Text(
        string='Description',
        required=True
    )
    
    # Resolution
    resolution = fields.Text(
        string='Resolution'
    )
    resolved_date = fields.Date(
        string='Resolved Date'
    )
    
    # Status
    state = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ], string='Status', default='open')
    
    # Photo
    photo_ids = fields.Many2many(
        'ir.attachment',
        string='Photos'
    )
