# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Contract(models.Model):
    """
    Contract - Sign project contract details.
    
    Tracks contract terms, payment schedule, change orders, and retainage.
    """
    _name = 'ps.contract'
    _description = 'Sign Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # =========================================================================
    # IDENTIFICATION
    # =========================================================================
    name = fields.Char(
        string='Contract Number',
        required=True,
        tracking=True
    )
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        ondelete='cascade'
    )
    opportunity_id = fields.Many2one(
        related='project_id.opportunity_id',
        string='Opportunity',
        store=True
    )
    
    # =========================================================================
    # PARTIES
    # =========================================================================
    gc_partner_id = fields.Many2one(
        related='project_id.gc_partner_id',
        string='General Contractor',
        store=True
    )
    
    # =========================================================================
    # CONTRACT TERMS
    # =========================================================================
    contract_date = fields.Date(
        string='Contract Date',
        tracking=True
    )
    contract_amount = fields.Float(
        string='Original Contract Amount',
        tracking=True
    )
    revised_amount = fields.Float(
        string='Revised Amount',
        compute='_compute_revised_amount',
        store=True
    )
    
    po_number = fields.Char(
        string='PO Number'
    )
    
    # =========================================================================
    # PAYMENT TERMS
    # =========================================================================
    payment_terms = fields.Selection([
        ('net30', 'Net 30'),
        ('net45', 'Net 45'),
        ('net60', 'Net 60'),
        ('progress', 'Progress Billing'),
        ('milestone', 'Milestone Billing'),
    ], string='Payment Terms', default='net30')
    
    retainage_percent = fields.Float(
        string='Retainage %',
        default=10.0
    )
    retainage_amount = fields.Float(
        string='Retainage Amount',
        compute='_compute_retainage',
        store=True
    )
    
    # =========================================================================
    # SCOPE
    # =========================================================================
    scope_description = fields.Text(
        string='Scope Description'
    )
    exclusions = fields.Text(
        string='Exclusions'
    )
    
    # =========================================================================
    # CHANGE ORDERS
    # =========================================================================
    change_order_ids = fields.One2many(
        'ps.change.order',
        'contract_id',
        string='Change Orders'
    )
    change_order_total = fields.Float(
        string='CO Total',
        compute='_compute_change_order_total',
        store=True
    )
    
    # =========================================================================
    # DOCUMENTS
    # =========================================================================
    contract_attachment_id = fields.Many2one(
        'ir.attachment',
        string='Contract Document'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('signed', 'Signed'),
        ('active', 'Active'),
        ('complete', 'Complete'),
        ('canceled', 'Canceled'),
    ], string='Status', default='draft', tracking=True)

    # =========================================================================
    # COMPUTED
    # =========================================================================
    
    @api.depends('contract_amount', 'change_order_total')
    def _compute_revised_amount(self):
        for contract in self:
            contract.revised_amount = contract.contract_amount + contract.change_order_total

    @api.depends('revised_amount', 'retainage_percent')
    def _compute_retainage(self):
        for contract in self:
            contract.retainage_amount = contract.revised_amount * (contract.retainage_percent / 100)

    @api.depends('change_order_ids.amount')
    def _compute_change_order_total(self):
        for contract in self:
            contract.change_order_total = sum(contract.change_order_ids.mapped('amount'))


class ChangeOrder(models.Model):
    """
    Change Order - Contract modifications.
    """
    _name = 'ps.change.order'
    _description = 'Change Order'
    _order = 'sequence, id'

    name = fields.Char(
        string='CO Number',
        required=True
    )
    contract_id = fields.Many2one(
        'ps.contract',
        string='Contract',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    # Details
    description = fields.Text(
        string='Description',
        required=True
    )
    reason = fields.Selection([
        ('scope', 'Scope Change'),
        ('rfi', 'RFI Response'),
        ('field', 'Field Condition'),
        ('owner', 'Owner Request'),
        ('error', 'Error/Omission'),
    ], string='Reason')
    
    # Amount
    amount = fields.Float(
        string='Amount',
        required=True
    )
    
    # Dates
    submitted_date = fields.Date(
        string='Submitted'
    )
    approved_date = fields.Date(
        string='Approved'
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft')
    
    # Sign Types affected
    sign_type_ids = fields.Many2many(
        'ps.sign.type',
        string='Affected Sign Types'
    )
