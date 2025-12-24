# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Estimate(models.Model):
    """
    Estimate - Cost estimate for a sign project.
    
    Created from CRM opportunity, contains detailed line items
    for each sign type with material, labor, and installation costs.
    """
    _name = 'ps.estimate'
    _description = 'Sign Estimate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # =========================================================================
    # IDENTIFICATION
    # =========================================================================
    name = fields.Char(
        string='Estimate Number',
        required=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('ps.estimate') or 'New',
        tracking=True
    )
    opportunity_id = fields.Many2one(
        'crm.lead',
        string='Opportunity',
        required=True,
        ondelete='cascade'
    )
    project_name = fields.Char(
        related='opportunity_id.name',
        string='Project Name'
    )
    
    # =========================================================================
    # DATES
    # =========================================================================
    date = fields.Date(
        string='Estimate Date',
        default=fields.Date.today,
        required=True
    )
    valid_until = fields.Date(
        string='Valid Until'
    )
    
    # =========================================================================
    # PARTIES
    # =========================================================================
    gc_partner_id = fields.Many2one(
        related='opportunity_id.gc_partner_id',
        string='General Contractor',
        store=True
    )
    
    # =========================================================================
    # LINES
    # =========================================================================
    line_ids = fields.One2many(
        'ps.estimate.line',
        'estimate_id',
        string='Estimate Lines'
    )
    
    # =========================================================================
    # TOTALS
    # =========================================================================
    material_total = fields.Float(
        string='Material Total',
        compute='_compute_totals',
        store=True
    )
    labor_total = fields.Float(
        string='Labor Total',
        compute='_compute_totals',
        store=True
    )
    install_total = fields.Float(
        string='Install Total',
        compute='_compute_totals',
        store=True
    )
    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_totals',
        store=True
    )
    
    # =========================================================================
    # MARKUP
    # =========================================================================
    markup_percent = fields.Float(
        string='Markup %',
        default=25.0
    )
    markup_amount = fields.Float(
        string='Markup Amount',
        compute='_compute_totals',
        store=True
    )
    
    # =========================================================================
    # FINAL
    # =========================================================================
    total = fields.Float(
        string='Estimate Total',
        compute='_compute_totals',
        store=True,
        tracking=True
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    state = fields.Selection([
        ('draft', 'Draft'),
        ('review', 'Under Review'),
        ('approved', 'Approved'),
        ('submitted', 'Submitted'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    ], string='Status', default='draft', tracking=True)
    
    # =========================================================================
    # NOTES
    # =========================================================================
    notes = fields.Text(
        string='Internal Notes'
    )
    terms = fields.Text(
        string='Terms & Conditions'
    )
    exclusions = fields.Text(
        string='Exclusions'
    )

    # =========================================================================
    # COMPUTED
    # =========================================================================
    
    @api.depends('line_ids.material_extended', 'line_ids.labor_extended', 
                 'line_ids.install_extended', 'markup_percent')
    def _compute_totals(self):
        for estimate in self:
            estimate.material_total = sum(estimate.line_ids.mapped('material_extended'))
            estimate.labor_total = sum(estimate.line_ids.mapped('labor_extended'))
            estimate.install_total = sum(estimate.line_ids.mapped('install_extended'))
            estimate.subtotal = estimate.material_total + estimate.labor_total + estimate.install_total
            estimate.markup_amount = estimate.subtotal * (estimate.markup_percent / 100)
            estimate.total = estimate.subtotal + estimate.markup_amount

    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def action_populate_from_sign_types(self):
        """Create estimate lines from opportunity's sign types"""
        self.ensure_one()
        EstimateLine = self.env['ps.estimate.line']
        
        for sign_type in self.opportunity_id.sign_type_ids:
            EstimateLine.create({
                'estimate_id': self.id,
                'sign_type_id': sign_type.id,
                'quantity': sign_type.quantity,
                'material_unit_cost': sign_type.unit_cost or 0,
            })
        
        return True

    def action_submit(self):
        """Mark estimate as submitted"""
        self.write({'state': 'submitted'})

    def action_approve(self):
        """Mark estimate as approved"""
        self.write({'state': 'approved'})


class EstimateLine(models.Model):
    """
    Estimate Line - Individual line item in an estimate.
    """
    _name = 'ps.estimate.line'
    _description = 'Estimate Line'
    _order = 'sequence, id'

    estimate_id = fields.Many2one(
        'ps.estimate',
        string='Estimate',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    # =========================================================================
    # SIGN TYPE REFERENCE
    # =========================================================================
    sign_type_id = fields.Many2one(
        'ps.sign.type',
        string='Sign Type'
    )
    description = fields.Char(
        string='Description'
    )
    
    # From sign type
    category_id = fields.Many2one(
        related='sign_type_id.category_id',
        string='Category'
    )
    dimensions_display = fields.Char(
        related='sign_type_id.dimensions_display',
        string='Size'
    )
    
    # =========================================================================
    # QUANTITY
    # =========================================================================
    quantity = fields.Integer(
        string='Qty',
        default=1
    )
    uom = fields.Selection([
        ('ea', 'Each'),
        ('sf', 'Sq Ft'),
        ('lf', 'Lin Ft'),
        ('set', 'Set'),
    ], string='UoM', default='ea')
    
    # =========================================================================
    # MATERIAL COSTS
    # =========================================================================
    material_unit_cost = fields.Float(
        string='Material Unit Cost'
    )
    material_extended = fields.Float(
        string='Material Extended',
        compute='_compute_extended',
        store=True
    )
    
    # =========================================================================
    # LABOR COSTS
    # =========================================================================
    labor_hours = fields.Float(
        string='Labor Hours'
    )
    labor_rate = fields.Float(
        string='Labor Rate',
        default=75.0
    )
    labor_extended = fields.Float(
        string='Labor Extended',
        compute='_compute_extended',
        store=True
    )
    
    # =========================================================================
    # INSTALLATION COSTS
    # =========================================================================
    install_hours = fields.Float(
        string='Install Hours'
    )
    install_rate = fields.Float(
        string='Install Rate',
        default=85.0
    )
    install_extended = fields.Float(
        string='Install Extended',
        compute='_compute_extended',
        store=True
    )
    
    # =========================================================================
    # LINE TOTAL
    # =========================================================================
    line_total = fields.Float(
        string='Line Total',
        compute='_compute_extended',
        store=True
    )
    
    # =========================================================================
    # NOTES
    # =========================================================================
    notes = fields.Char(
        string='Notes'
    )

    # =========================================================================
    # COMPUTED
    # =========================================================================
    
    @api.depends('quantity', 'material_unit_cost', 'labor_hours', 'labor_rate',
                 'install_hours', 'install_rate')
    def _compute_extended(self):
        for line in self:
            line.material_extended = line.quantity * line.material_unit_cost
            line.labor_extended = line.labor_hours * line.labor_rate
            line.install_extended = line.install_hours * line.install_rate
            line.line_total = line.material_extended + line.labor_extended + line.install_extended

    @api.onchange('sign_type_id')
    def _onchange_sign_type_id(self):
        """Auto-fill from sign type"""
        if self.sign_type_id:
            self.description = self.sign_type_id.name
            self.quantity = self.sign_type_id.quantity
            if self.sign_type_id.unit_cost:
                self.material_unit_cost = self.sign_type_id.unit_cost
