# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RFI(models.Model):
    """
    RFI - Request for Information.
    
    Track questions and clarifications during project execution.
    """
    _name = 'ps.rfi'
    _description = 'Request for Information'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # =========================================================================
    # IDENTIFICATION
    # =========================================================================
    name = fields.Char(
        string='RFI Number',
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
    # QUESTION
    # =========================================================================
    subject = fields.Char(
        string='Subject',
        required=True
    )
    question = fields.Html(
        string='Question',
        required=True
    )
    
    # Reference
    spec_section = fields.Char(
        string='Spec Section'
    )
    drawing_reference = fields.Char(
        string='Drawing Reference'
    )
    sign_type_ids = fields.Many2many(
        'ps.sign.type',
        string='Related Sign Types'
    )
    
    # =========================================================================
    # DATES
    # =========================================================================
    submitted_date = fields.Date(
        string='Submitted',
        default=fields.Date.today,
        tracking=True
    )
    needed_by = fields.Date(
        string='Response Needed By'
    )
    response_date = fields.Date(
        string='Response Received'
    )
    
    # =========================================================================
    # ADDRESSED TO
    # =========================================================================
    addressed_to = fields.Selection([
        ('architect', 'Architect'),
        ('gc', 'General Contractor'),
        ('owner', 'Owner'),
        ('engineer', 'Engineer'),
        ('consultant', 'Consultant'),
    ], string='Addressed To', default='architect')
    
    contact_id = fields.Many2one(
        'res.partner',
        string='Contact'
    )
    
    # =========================================================================
    # RESPONSE
    # =========================================================================
    response = fields.Html(
        string='Response'
    )
    responded_by = fields.Char(
        string='Responded By'
    )
    
    # =========================================================================
    # IMPACT
    # =========================================================================
    cost_impact = fields.Boolean(
        string='Cost Impact',
        default=False
    )
    cost_amount = fields.Float(
        string='Cost Amount'
    )
    schedule_impact = fields.Boolean(
        string='Schedule Impact',
        default=False
    )
    schedule_days = fields.Integer(
        string='Days Impact'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('answered', 'Answered'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)
    
    # =========================================================================
    # ATTACHMENTS
    # =========================================================================
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'ps_rfi_attachment_rel',
        'rfi_id',
        'attachment_id',
        string='Attachments'
    )

    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def action_submit(self):
        """Submit RFI"""
        self.write({
            'state': 'submitted',
            'submitted_date': fields.Date.today(),
        })

    def action_mark_answered(self):
        """Mark as answered"""
        self.write({
            'state': 'answered',
            'response_date': fields.Date.today(),
        })

    def action_close(self):
        """Close RFI"""
        self.write({'state': 'closed'})
