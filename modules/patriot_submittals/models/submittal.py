# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Submittal(models.Model):
    """
    Submittal - Submittal package for architect approval.
    
    Contains shop drawings, product data, and samples for review.
    Follows standard AIA G810 submittal procedures.
    """
    _name = 'ps.submittal'
    _description = 'Submittal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # =========================================================================
    # IDENTIFICATION
    # =========================================================================
    name = fields.Char(
        string='Submittal Number',
        required=True,
        tracking=True
    )
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        ondelete='cascade'
    )
    project_name = fields.Char(
        related='project_id.name',
        string='Project Name'
    )
    
    # =========================================================================
    # SPEC SECTION
    # =========================================================================
    spec_section = fields.Char(
        string='Spec Section',
        default='10 14 00',
        help='CSI specification section (e.g., 10 14 00 - Signage)'
    )
    spec_title = fields.Char(
        string='Spec Title',
        default='Interior Signage'
    )
    
    # =========================================================================
    # SUBMITTAL CONTENT
    # =========================================================================
    submittal_type = fields.Selection([
        ('shop', 'Shop Drawings'),
        ('product', 'Product Data'),
        ('sample', 'Samples'),
        ('mock', 'Mock-Up'),
        ('certificate', 'Certificates'),
        ('test', 'Test Reports'),
        ('warranty', 'Warranty'),
        ('maintenance', 'Maintenance Data'),
    ], string='Type', default='shop', required=True)
    
    description = fields.Text(
        string='Description'
    )
    
    # =========================================================================
    # SIGN TYPES INCLUDED
    # =========================================================================
    sign_type_ids = fields.Many2many(
        'ps.sign.type',
        string='Sign Types Included'
    )
    sign_type_count = fields.Integer(
        string='Sign Types',
        compute='_compute_sign_type_count'
    )
    
    # =========================================================================
    # DOCUMENTS
    # =========================================================================
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'ps_submittal_attachment_rel',
        'submittal_id',
        'attachment_id',
        string='Attachments'
    )
    attachment_count = fields.Integer(
        string='Attachments',
        compute='_compute_attachment_count'
    )
    
    # =========================================================================
    # REVISION TRACKING
    # =========================================================================
    revision = fields.Integer(
        string='Revision',
        default=0,
        tracking=True
    )
    revision_notes = fields.Text(
        string='Revision Notes'
    )
    previous_submittal_id = fields.Many2one(
        'ps.submittal',
        string='Previous Revision'
    )
    
    # =========================================================================
    # DATES
    # =========================================================================
    submitted_date = fields.Date(
        string='Submitted',
        tracking=True
    )
    due_date = fields.Date(
        string='Response Due'
    )
    response_date = fields.Date(
        string='Response Received',
        tracking=True
    )
    
    # =========================================================================
    # RESPONSE
    # =========================================================================
    response = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('approved_noted', 'Approved as Noted'),
        ('revise', 'Revise and Resubmit'),
        ('rejected', 'Rejected'),
        ('void', 'Void'),
    ], string='Response', default='pending', tracking=True)
    
    response_notes = fields.Text(
        string='Response Notes'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready to Submit'),
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed'),
    ], string='Status', default='draft', tracking=True)
    
    is_approved = fields.Boolean(
        string='Approved',
        compute='_compute_is_approved',
        store=True
    )

    # =========================================================================
    # COMPUTED
    # =========================================================================
    
    @api.depends('sign_type_ids')
    def _compute_sign_type_count(self):
        for submittal in self:
            submittal.sign_type_count = len(submittal.sign_type_ids)

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for submittal in self:
            submittal.attachment_count = len(submittal.attachment_ids)

    @api.depends('response')
    def _compute_is_approved(self):
        for submittal in self:
            submittal.is_approved = submittal.response in ['approved', 'approved_noted']

    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def action_submit(self):
        """Mark as submitted"""
        self.write({
            'state': 'submitted',
            'submitted_date': fields.Date.today(),
        })

    def action_mark_reviewed(self):
        """Mark as reviewed"""
        self.write({
            'state': 'reviewed',
            'response_date': fields.Date.today(),
        })

    def action_create_revision(self):
        """Create new revision from this submittal"""
        self.ensure_one()
        new_submittal = self.copy({
            'name': f"{self.name}-R{self.revision + 1}",
            'revision': self.revision + 1,
            'previous_submittal_id': self.id,
            'state': 'draft',
            'response': 'pending',
            'submitted_date': False,
            'response_date': False,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ps.submittal',
            'res_id': new_submittal.id,
            'view_mode': 'form',
            'target': 'current',
        }


class SubmittalItem(models.Model):
    """
    Submittal Item - Individual item within a submittal package.
    """
    _name = 'ps.submittal.item'
    _description = 'Submittal Item'
    _order = 'sequence, id'

    submittal_id = fields.Many2one(
        'ps.submittal',
        string='Submittal',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    # Item details
    sign_type_id = fields.Many2one(
        'ps.sign.type',
        string='Sign Type'
    )
    description = fields.Char(
        string='Description',
        required=True
    )
    sheet_number = fields.Char(
        string='Sheet Number'
    )
    
    # Status
    response = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('noted', 'Approved as Noted'),
        ('revise', 'Revise'),
        ('rejected', 'Rejected'),
    ], string='Response', default='pending')
    
    notes = fields.Text(
        string='Notes'
    )
