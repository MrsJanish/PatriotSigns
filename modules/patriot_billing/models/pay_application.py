# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PayApplication(models.Model):
    """
    Pay Application - AIA-style progress billing.
    
    Based on AIA G702/G703 format for construction billing.
    """
    _name = 'ps.pay.application'
    _description = 'Pay Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'application_number desc'

    # =========================================================================
    # IDENTIFICATION
    # =========================================================================
    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True
    )
    application_number = fields.Integer(
        string='Application #',
        required=True,
        tracking=True
    )
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        ondelete='cascade'
    )
    contract_id = fields.Many2one(
        'ps.contract',
        string='Contract'
    )
    
    # =========================================================================
    # PERIOD
    # =========================================================================
    period_start = fields.Date(
        string='Period Start',
        required=True
    )
    period_end = fields.Date(
        string='Period End',
        required=True
    )
    
    # =========================================================================
    # LINE ITEMS
    # =========================================================================
    line_ids = fields.One2many(
        'ps.pay.application.line',
        'pay_application_id',
        string='Line Items'
    )
    
    # =========================================================================
    # SUMMARY AMOUNTS
    # =========================================================================
    original_contract = fields.Float(
        string='Original Contract Sum',
        compute='_compute_totals',
        store=True
    )
    change_orders = fields.Float(
        string='Net Change Orders',
        compute='_compute_totals',
        store=True
    )
    revised_contract = fields.Float(
        string='Contract Sum to Date',
        compute='_compute_totals',
        store=True
    )
    
    # This period
    work_completed = fields.Float(
        string='Work Completed This Period',
        compute='_compute_totals',
        store=True
    )
    materials_stored = fields.Float(
        string='Materials Stored This Period',
        compute='_compute_totals',
        store=True
    )
    this_period_total = fields.Float(
        string='Total This Period',
        compute='_compute_totals',
        store=True
    )
    
    # Totals
    total_completed_stored = fields.Float(
        string='Total Completed & Stored',
        compute='_compute_totals',
        store=True
    )
    percent_complete = fields.Float(
        string='% Complete',
        compute='_compute_totals',
        store=True
    )
    
    # Retainage
    retainage_percent = fields.Float(
        string='Retainage %',
        default=10.0
    )
    retainage_amount = fields.Float(
        string='Retainage',
        compute='_compute_totals',
        store=True
    )
    
    # Less previous
    previous_applications = fields.Float(
        string='Less Previous Certificates',
        compute='_compute_previous_applications',
        store=True
    )
    
    # Current due
    current_payment_due = fields.Float(
        string='Current Payment Due',
        compute='_compute_totals',
        store=True,
        tracking=True
    )
    
    # =========================================================================
    # INVOICE LINK
    # =========================================================================
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        readonly=True
    )
    invoice_state = fields.Selection(
        related='invoice_id.state',
        string='Invoice Status'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('invoiced', 'Invoiced'),
        ('paid', 'Paid'),
    ], string='Status', default='draft', tracking=True)
    
    submitted_date = fields.Date(
        string='Submitted Date'
    )
    approved_date = fields.Date(
        string='Approved Date'
    )
    
    notes = fields.Text(
        string='Notes'
    )

    # =========================================================================
    # COMPUTED
    # =========================================================================
    
    @api.depends('project_id', 'application_number')
    def _compute_name(self):
        for pa in self:
            if pa.project_id and pa.application_number:
                pa.name = f"{pa.project_id.name} - App #{pa.application_number}"
            else:
                pa.name = f"Application #{pa.application_number or 0}"

    @api.depends('line_ids.scheduled_value', 'line_ids.this_period_work',
                 'line_ids.this_period_materials', 'line_ids.completed_to_date',
                 'retainage_percent')
    def _compute_totals(self):
        for pa in self:
            lines = pa.line_ids
            
            pa.original_contract = sum(lines.filtered(lambda l: not l.is_change_order).mapped('scheduled_value'))
            pa.change_orders = sum(lines.filtered(lambda l: l.is_change_order).mapped('scheduled_value'))
            pa.revised_contract = pa.original_contract + pa.change_orders
            
            pa.work_completed = sum(lines.mapped('this_period_work'))
            pa.materials_stored = sum(lines.mapped('this_period_materials'))
            pa.this_period_total = pa.work_completed + pa.materials_stored
            
            pa.total_completed_stored = sum(lines.mapped('completed_to_date'))
            
            if pa.revised_contract:
                pa.percent_complete = (pa.total_completed_stored / pa.revised_contract) * 100
            else:
                pa.percent_complete = 0
            
            pa.retainage_amount = pa.total_completed_stored * (pa.retainage_percent / 100)
            
            # Current payment due = Total - Retainage - Previous
            pa.current_payment_due = pa.total_completed_stored - pa.retainage_amount - pa.previous_applications

    @api.depends('project_id', 'application_number')
    def _compute_previous_applications(self):
        for pa in self:
            previous = self.search([
                ('project_id', '=', pa.project_id.id),
                ('application_number', '<', pa.application_number),
                ('state', 'in', ['approved', 'invoiced', 'paid']),
            ])
            pa.previous_applications = sum(previous.mapped('current_payment_due'))

    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def action_submit(self):
        """Submit pay application"""
        self.write({
            'state': 'submitted',
            'submitted_date': fields.Date.today(),
        })

    def action_approve(self):
        """Approve pay application"""
        self.write({
            'state': 'approved',
            'approved_date': fields.Date.today(),
        })

    def action_create_invoice(self):
        """Create invoice from pay application"""
        self.ensure_one()
        
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.project_id.gc_partner_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': f"Pay Application #{self.application_number}: {self.project_id.name}",
                'quantity': 1,
                'price_unit': self.current_payment_due,
            })],
        })
        
        self.write({
            'state': 'invoiced',
            'invoice_id': invoice.id,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }


class PayApplicationLine(models.Model):
    """
    Pay Application Line - Individual SOV line item billing.
    """
    _name = 'ps.pay.application.line'
    _description = 'Pay Application Line'
    _order = 'sequence, id'

    pay_application_id = fields.Many2one(
        'ps.pay.application',
        string='Pay Application',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    # SOV Reference
    sov_line_id = fields.Many2one(
        'ps.sov.line',
        string='SOV Line'
    )
    description = fields.Char(
        string='Description',
        required=True
    )
    is_change_order = fields.Boolean(
        string='Is CO',
        default=False
    )
    
    # Values
    scheduled_value = fields.Float(
        string='Scheduled Value'
    )
    
    # Previous
    previous_completed = fields.Float(
        string='Previous Completed'
    )
    
    # This period
    this_period_work = fields.Float(
        string='Work This Period'
    )
    this_period_materials = fields.Float(
        string='Materials Stored'
    )
    
    # Totals
    completed_to_date = fields.Float(
        string='Completed to Date',
        compute='_compute_completed',
        store=True
    )
    percent_complete = fields.Float(
        string='% Complete',
        compute='_compute_completed',
        store=True
    )
    balance_to_finish = fields.Float(
        string='Balance to Finish',
        compute='_compute_completed',
        store=True
    )

    @api.depends('scheduled_value', 'previous_completed', 'this_period_work', 'this_period_materials')
    def _compute_completed(self):
        for line in self:
            line.completed_to_date = line.previous_completed + line.this_period_work + line.this_period_materials
            if line.scheduled_value:
                line.percent_complete = (line.completed_to_date / line.scheduled_value) * 100
            else:
                line.percent_complete = 0
            line.balance_to_finish = line.scheduled_value - line.completed_to_date
