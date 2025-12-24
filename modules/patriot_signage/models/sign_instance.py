# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SignInstance(models.Model):
    """
    Sign Instance - Individual physical sign installation.
    
    Each instance represents ONE physical sign at ONE specific location.
    Multiple instances can belong to the same sign type.
    
    Example: Sign Type "A" (Room ID) with quantity 50 can have 50 instances,
    each with its own room number, copy content, and installation status.
    """
    _name = 'ps.sign.instance'
    _description = 'Sign Instance'
    _order = 'sign_type_id, install_sequence, id'
    _inherit = ['mail.thread']

    # =========================================================================
    # IDENTIFICATION
    # =========================================================================
    name = fields.Char(
        string='Instance ID',
        compute='_compute_name',
        store=True
    )
    sign_type_id = fields.Many2one(
        'ps.sign.type',
        string='Sign Type',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    mark_id = fields.Char(
        string='Sign Mark/ID',
        help='ID shown on architectural plans'
    )

    # =========================================================================
    # PROJECT REFERENCE (from sign type)
    # =========================================================================
    opportunity_id = fields.Many2one(
        related='sign_type_id.opportunity_id',
        string='Project',
        store=True
    )
    project_alias = fields.Char(
        related='sign_type_id.project_alias',
        string='Project Alias',
        store=True
    )
    category_id = fields.Many2one(
        related='sign_type_id.category_id',
        string='Category',
        store=True
    )
    dimensions_display = fields.Char(
        related='sign_type_id.dimensions_display',
        string='Size'
    )

    # =========================================================================
    # LOCATION
    # =========================================================================
    location_id = fields.Many2one(
        'ps.location',
        string='Location',
        domain="[('project_id', '=', opportunity_id)]"
    )
    building = fields.Char(
        string='Building'
    )
    floor = fields.Char(
        string='Floor/Level'
    )
    room_number_plans = fields.Char(
        string='Room # (Plans)',
        help='Room number per architectural drawings'
    )
    room_number_actual = fields.Char(
        string='Room # (Actual)',
        help='Actual/revised room number'
    )
    room_name_plans = fields.Char(
        string='Room Name (Plans)',
        help='Room name per architectural drawings'
    )
    room_name_actual = fields.Char(
        string='Room Name (Actual)',
        help='Actual/revised room name'
    )
    door_id = fields.Char(
        string='Door ID',
        help='Adjacent door number'
    )
    wall_location = fields.Selection([
        ('latch', 'Latch Side'),
        ('strike', 'Strike Side'),
        ('above', 'Above Door'),
        ('adjacent', 'Adjacent Wall'),
        ('corridor', 'Corridor Side'),
        ('room', 'Room Side'),
    ], string='Wall Location')
    
    location_notes = fields.Char(
        string='Location Notes'
    )

    # =========================================================================
    # COPY CONTENT
    # =========================================================================
    copy_line_1 = fields.Char(
        string='Copy Line 1'
    )
    copy_line_2 = fields.Char(
        string='Copy Line 2'
    )
    copy_line_3 = fields.Char(
        string='Copy Line 3'
    )
    copy_line_4 = fields.Char(
        string='Copy Line 4'
    )
    copy_line_5 = fields.Char(
        string='Copy Line 5'
    )
    copy_full = fields.Text(
        string='Full Copy',
        compute='_compute_copy_full',
        store=True
    )
    has_custom_copy = fields.Boolean(
        string='Custom Copy',
        default=False
    )
    arrow_direction = fields.Selection([
        ('none', 'None'),
        ('up', 'Up'),
        ('down', 'Down'),
        ('left', 'Left'),
        ('right', 'Right'),
        ('up_left', 'Up-Left'),
        ('up_right', 'Up-Right'),
        ('down_left', 'Down-Left'),
        ('down_right', 'Down-Right'),
    ], string='Arrow Direction', default='none')
    
    pictogram_code = fields.Char(
        string='Pictogram Code'
    )

    # =========================================================================
    # BID/PHASING
    # =========================================================================
    bid_package = fields.Selection([
        ('base', 'Base Bid'),
        ('alt1', 'Alternate 1'),
        ('alt2', 'Alternate 2'),
        ('alt3', 'Alternate 3'),
        ('additive', 'Additive'),
        ('deductive', 'Deductive'),
    ], string='Bid Package', default='base')
    phase = fields.Char(
        string='Phase'
    )
    added_post_bid = fields.Boolean(
        string='Added Post-Bid',
        default=False
    )

    # =========================================================================
    # STATUS & QC
    # =========================================================================
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('production', 'In Production'),
        ('qc', 'QC Check'),
        ('shipped', 'Shipped'),
        ('installed', 'Installed'),
    ], string='Status', default='draft', tracking=True)
    
    approved = fields.Boolean(
        string='Approved',
        default=False
    )
    approved_date = fields.Date(
        string='Approved Date'
    )
    quality_checked = fields.Boolean(
        string='QC Passed',
        default=False
    )
    qc_date = fields.Date(
        string='QC Date'
    )
    qc_notes = fields.Text(
        string='QC Notes'
    )

    # =========================================================================
    # INSTALLATION
    # =========================================================================
    install_sequence = fields.Integer(
        string='Install Sequence',
        default=0,
        help='Order for installation'
    )
    installed = fields.Boolean(
        string='Installed',
        default=False
    )
    installed_date = fields.Date(
        string='Installed Date'
    )
    install_notes = fields.Text(
        string='Install Notes'
    )

    # =========================================================================
    # BACKER
    # =========================================================================
    needs_backer = fields.Boolean(
        string='Needs Backer',
        default=False
    )
    backer_instance_id = fields.Many2one(
        'ps.sign.instance',
        string='Backer Instance'
    )

    # =========================================================================
    # PRODUCTION NOTES
    # =========================================================================
    production_notes = fields.Text(
        string='Production Notes'
    )
    remarks = fields.Text(
        string='Remarks'
    )

    # =========================================================================
    # COMPUTED FIELDS
    # =========================================================================
    
    @api.depends('sign_type_id.name', 'sequence', 'room_number_plans')
    def _compute_name(self):
        for record in self:
            if record.sign_type_id:
                if record.room_number_plans:
                    record.name = f"{record.sign_type_id.name} - {record.room_number_plans}"
                else:
                    record.name = f"{record.sign_type_id.name} #{record.sequence or record.id or 0}"
            else:
                record.name = f"Instance #{record.id or 0}"

    @api.depends('copy_line_1', 'copy_line_2', 'copy_line_3', 'copy_line_4', 'copy_line_5')
    def _compute_copy_full(self):
        for record in self:
            lines = [
                record.copy_line_1,
                record.copy_line_2,
                record.copy_line_3,
                record.copy_line_4,
                record.copy_line_5,
            ]
            record.copy_full = '\n'.join(filter(None, lines))

    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def action_approve(self):
        """Mark instance as approved"""
        self.write({
            'state': 'approved',
            'approved': True,
            'approved_date': fields.Date.today(),
        })

    def action_mark_installed(self):
        """Mark instance as installed"""
        self.write({
            'state': 'installed',
            'installed': True,
            'installed_date': fields.Date.today(),
        })
