# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Location(models.Model):
    """
    Location - Hierarchical project location structure.
    
    Represents physical locations within a project: 
    Jobsite → Building → Floor → Area → Room
    
    Uses Odoo's parent_store for efficient hierarchical queries.
    """
    _name = 'ps.location'
    _description = 'Project Location'
    _parent_name = 'parent_id'
    _parent_store = True
    _order = 'project_id, sequence, name'

    # =========================================================================
    # IDENTIFICATION
    # =========================================================================
    name = fields.Char(
        string='Location Name',
        required=True
    )
    display_name_full = fields.Char(
        string='Full Name',
        compute='_compute_display_name_full',
        store=True
    )
    project_id = fields.Many2one(
        'crm.lead',
        string='Project',
        required=True,
        ondelete='cascade'
    )
    project_alias = fields.Char(
        related='project_id.project_alias',
        string='Project Alias',
        store=True
    )

    # =========================================================================
    # HIERARCHY
    # =========================================================================
    parent_id = fields.Many2one(
        'ps.location',
        string='Parent Location',
        ondelete='cascade',
        domain="[('project_id', '=', project_id)]"
    )
    parent_path = fields.Char(
        index=True
    )
    child_ids = fields.One2many(
        'ps.location',
        'parent_id',
        string='Sub-Locations'
    )
    child_count = fields.Integer(
        string='Sub-Location Count',
        compute='_compute_child_count'
    )

    # =========================================================================
    # TYPE
    # =========================================================================
    location_type = fields.Selection([
        ('site', 'Jobsite'),
        ('building', 'Building'),
        ('floor', 'Floor/Level'),
        ('area', 'Area/Wing'),
        ('room', 'Room'),
    ], string='Location Type', required=True, default='room')

    # =========================================================================
    # ROOM DETAILS
    # =========================================================================
    room_number = fields.Char(
        string='Room Number'
    )
    room_name = fields.Char(
        string='Room Name'
    )
    room_number_arch = fields.Char(
        string='Arch Room Number',
        help='Room number per architectural reference'
    )
    room_name_arch = fields.Char(
        string='Arch Room Name',
        help='Room name per architectural reference'
    )
    
    # Revisions
    is_revised = fields.Boolean(
        string='Room Revised',
        default=False
    )
    original_room_number = fields.Char(
        string='Original Room #'
    )
    original_room_name = fields.Char(
        string='Original Room Name'
    )
    revision_of_id = fields.Many2one(
        'ps.location',
        string='Revision Of'
    )

    # =========================================================================
    # ADDRESS (for jobsite type)
    # =========================================================================
    address = fields.Char(
        string='Address'
    )
    city = fields.Char(
        string='City'
    )
    state_id = fields.Many2one(
        'res.country.state',
        string='State',
        domain="[('country_id.code', '=', 'US')]"
    )
    zip_code = fields.Char(
        string='ZIP Code'
    )

    # =========================================================================
    # ORGANIZATION
    # =========================================================================
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    internal_id = fields.Integer(
        string='Internal ID',
        help='Legacy internal reference'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    notes = fields.Text(
        string='Notes'
    )

    # =========================================================================
    # RELATED SIGNS
    # =========================================================================
    instance_ids = fields.One2many(
        'ps.sign.instance',
        'location_id',
        string='Sign Instances'
    )
    instance_count = fields.Integer(
        string='Signs',
        compute='_compute_instance_count'
    )

    # =========================================================================
    # COMPUTED FIELDS
    # =========================================================================
    
    @api.depends('name', 'parent_id', 'parent_id.name')
    def _compute_display_name_full(self):
        for record in self:
            if record.parent_id:
                record.display_name_full = f"{record.parent_id.name} / {record.name}"
            else:
                record.display_name_full = record.name

    @api.depends('child_ids')
    def _compute_child_count(self):
        for record in self:
            record.child_count = len(record.child_ids)

    @api.depends('instance_ids')
    def _compute_instance_count(self):
        for record in self:
            record.instance_count = len(record.instance_ids)

    # =========================================================================
    # NAME_GET
    # =========================================================================
    
    def name_get(self):
        """Show hierarchical path in dropdowns"""
        result = []
        for record in self:
            if record.location_type == 'room' and record.room_number:
                name = f"{record.room_number} - {record.name}" if record.name != record.room_number else record.room_number
            else:
                name = record.name
            
            # Add parent path for context
            if record.parent_id:
                name = f"{record.parent_id.name} / {name}"
            
            result.append((record.id, name))
        return result
