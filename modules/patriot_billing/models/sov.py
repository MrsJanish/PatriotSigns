# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SOV(models.Model):
    """
    SOV - Schedule of Values for a project.
    
    Defines the line items for progress billing.
    """
    _name = 'ps.sov'
    _description = 'Schedule of Values'
    _inherit = ['mail.thread']
    _order = 'project_id, id'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True
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
    
    # Lines
    line_ids = fields.One2many(
        'ps.sov.line',
        'sov_id',
        string='Line Items'
    )
    
    # Totals
    total_value = fields.Float(
        string='Total Value',
        compute='_compute_total',
        store=True
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
    ], string='Status', default='draft', tracking=True)

    @api.depends('project_id')
    def _compute_name(self):
        for sov in self:
            sov.name = f"SOV - {sov.project_id.name}" if sov.project_id else "New SOV"

    @api.depends('line_ids.scheduled_value')
    def _compute_total(self):
        for sov in self:
            sov.total_value = sum(sov.line_ids.mapped('scheduled_value'))

    def action_populate_from_sign_types(self):
        """Create SOV lines from project sign types"""
        self.ensure_one()
        SOVLine = self.env['ps.sov.line']
        
        if self.project_id.opportunity_id:
            sequence = 10
            for sign_type in self.project_id.opportunity_id.sign_type_ids:
                SOVLine.create({
                    'sov_id': self.id,
                    'sequence': sequence,
                    'description': f"{sign_type.name} - {sign_type.category_id.name or ''}",
                    'sign_type_id': sign_type.id,
                    'scheduled_value': sign_type.extended_price,
                })
                sequence += 10
        
        return True


class SOVLine(models.Model):
    """
    SOV Line - Individual line item in Schedule of Values.
    """
    _name = 'ps.sov.line'
    _description = 'SOV Line'
    _order = 'sov_id, sequence, id'

    sov_id = fields.Many2one(
        'ps.sov',
        string='SOV',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(
        string='#',
        default=10
    )
    
    # Description
    description = fields.Char(
        string='Description of Work',
        required=True
    )
    sign_type_id = fields.Many2one(
        'ps.sign.type',
        string='Sign Type'
    )
    
    # Value
    scheduled_value = fields.Float(
        string='Scheduled Value'
    )
    
    # Change order flag
    is_change_order = fields.Boolean(
        string='Change Order',
        default=False
    )
    change_order_number = fields.Char(
        string='CO #'
    )
    
    # Billing progress (computed from pay applications)
    billed_to_date = fields.Float(
        string='Billed to Date',
        compute='_compute_billed'
    )
    remaining = fields.Float(
        string='Remaining',
        compute='_compute_billed'
    )

    def _compute_billed(self):
        PayAppLine = self.env['ps.pay.application.line']
        for line in self:
            app_lines = PayAppLine.search([('sov_line_id', '=', line.id)])
            line.billed_to_date = sum(app_lines.mapped('completed_to_date'))
            line.remaining = line.scheduled_value - line.billed_to_date
