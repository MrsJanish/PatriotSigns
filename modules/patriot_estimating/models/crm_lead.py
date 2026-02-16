# -*- coding: utf-8 -*-
from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # =========================================================================
    # ESTIMATE RELATIONSHIP
    # =========================================================================
    estimate_ids = fields.One2many(
        'ps.estimate', 'opportunity_id', string='Estimates')
    estimate_count = fields.Integer(
        compute='_compute_estimate_count')
    estimate_line_ids = fields.One2many(
        'ps.estimate.line', compute='_compute_estimate_line_ids',
        string='Estimate Lines')
    current_estimate_id = fields.Many2one(
        'ps.estimate', compute='_compute_current_estimate',
        string='Current Estimate')

    # =========================================================================
    # STAGE-DRIVEN VIEW SWITCHING
    # =========================================================================
    is_estimating_stage = fields.Boolean(
        compute='_compute_is_estimating_stage')

    # =========================================================================
    # RELATED ESTIMATE FIELDS — surfaces the full estimate on the CRM form
    # =========================================================================
    # Header
    estimate_name = fields.Char(
        related='current_estimate_id.name', string='Estimate #', readonly=True)
    estimate_state = fields.Selection(
        related='current_estimate_id.state', string='Estimate Status', readonly=True)
    estimate_date = fields.Date(
        related='current_estimate_id.date', string='Estimate Date', readonly=True)
    estimate_valid_until = fields.Date(
        related='current_estimate_id.valid_until', string='Valid Until', readonly=True)

    # Shop Labor
    est_total_molds = fields.Integer(
        related='current_estimate_id.total_molds', string='Total Molds', readonly=True)
    est_mold_time_minutes = fields.Float(
        related='current_estimate_id.mold_time_minutes', string='Time per Mold (min)', readonly=False)
    est_shop_rate = fields.Float(
        related='current_estimate_id.shop_rate', string='Shop Rate ($/hr)', readonly=False)
    est_shop_labor_total = fields.Float(
        related='current_estimate_id.shop_labor_total', string='Shop Labor Total', readonly=True)

    # Travel
    est_travel_miles = fields.Float(
        related='current_estimate_id.travel_miles', string='Travel Miles', readonly=False)
    est_travel_rate = fields.Float(
        related='current_estimate_id.travel_rate', string='Mileage Rate', readonly=False)
    est_travel_trips = fields.Integer(
        related='current_estimate_id.travel_trips', string='# Trips', readonly=False)
    est_travel_total = fields.Float(
        related='current_estimate_id.travel_total', string='Travel Total', readonly=True)

    # Installation
    est_install_crew_id = fields.Many2one(
        related='current_estimate_id.install_crew_id', string='Install Crew', readonly=False)
    est_install_crew_size = fields.Integer(
        related='current_estimate_id.install_crew_size', string='Crew Size', readonly=True)
    est_install_rate = fields.Float(
        related='current_estimate_id.install_rate', string='Install Rate', readonly=False)
    est_install_hours = fields.Float(
        related='current_estimate_id.install_hours', string='Install Hours', readonly=False)
    est_install_total = fields.Float(
        related='current_estimate_id.install_total', string='Install Total', readonly=True)

    # Equipment
    est_needs_equipment = fields.Boolean(
        related='current_estimate_id.needs_equipment', string='Equipment Needed', readonly=False)
    est_equipment_type = fields.Selection(
        related='current_estimate_id.equipment_type', string='Equipment Type', readonly=False)
    est_equipment_days = fields.Float(
        related='current_estimate_id.equipment_days', string='Rental Days', readonly=False)
    est_equipment_daily_rate = fields.Float(
        related='current_estimate_id.equipment_daily_rate', string='Daily Rate', readonly=False)
    est_equipment_delivery = fields.Float(
        related='current_estimate_id.equipment_delivery', string='Delivery/Pickup', readonly=False)
    est_equipment_total = fields.Float(
        related='current_estimate_id.equipment_total', string='Equipment Total', readonly=True)

    # Summary Totals
    est_signage_total = fields.Float(
        related='current_estimate_id.signage_total', string='Signage Total', readonly=True)
    estimate_total = fields.Float(
        related='current_estimate_id.total', string='Estimate Total', readonly=True)
    estimate_profit_amount = fields.Float(
        related='current_estimate_id.profit_amount', string='Profit $', readonly=True)
    estimate_profit_margin_pct = fields.Float(
        related='current_estimate_id.profit_margin_pct', string='Margin %', readonly=True)

    # Terms & Notes
    est_terms = fields.Text(
        related='current_estimate_id.terms', string='Terms & Conditions', readonly=False)
    est_exclusions = fields.Text(
        related='current_estimate_id.exclusions', string='Exclusions', readonly=False)
    est_notes = fields.Text(
        related='current_estimate_id.notes', string='Internal Notes', readonly=False)

    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================
    @api.depends('stage_id')
    def _compute_is_estimating_stage(self):
        estimating_stage = self.env.ref(
            'patriot_crm.stage_estimating', raise_if_not_found=False)
        for lead in self:
            lead.is_estimating_stage = (
                estimating_stage and lead.stage_id == estimating_stage)

    @api.depends('estimate_ids')
    def _compute_estimate_count(self):
        for lead in self:
            lead.estimate_count = len(lead.estimate_ids)

    @api.depends('estimate_ids', 'estimate_ids.line_ids')
    def _compute_estimate_line_ids(self):
        for lead in self:
            lead.estimate_line_ids = lead.estimate_ids.mapped('line_ids')

    @api.depends('estimate_ids')
    def _compute_current_estimate(self):
        for lead in self:
            active = lead.estimate_ids.filtered(lambda e: e.state != 'lost')
            lead.current_estimate_id = active[:1] if active else False

    # =========================================================================
    # ACTIONS
    # =========================================================================
    def action_open_lead_or_estimate(self):
        self.ensure_one()
        if self.estimate_count > 0:
            return self.action_view_estimates()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
        }

    def action_view_estimates(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'patriot_estimating.ps_estimate_action')
        action['domain'] = [('opportunity_id', '=', self.id)]
        action['context'] = {'default_opportunity_id': self.id}
        if self.estimate_count == 1:
            action['view_mode'] = 'form'
            action['views'] = [(False, 'form')]
            action['res_id'] = self.estimate_ids[0].id
        return action

    # =========================================================================
    # ESTIMATE WORKFLOW BUTTONS (proxy to current estimate)
    # =========================================================================
    def action_estimate_populate(self):
        self.ensure_one()
        if self.current_estimate_id:
            self.current_estimate_id.action_populate_from_sign_types()

    def action_estimate_recalculate(self):
        self.ensure_one()
        if self.current_estimate_id:
            self.current_estimate_id.action_recalculate()

    def action_estimate_approve(self):
        self.ensure_one()
        if self.current_estimate_id:
            self.current_estimate_id.action_approve()

    def action_estimate_submit(self):
        self.ensure_one()
        if self.current_estimate_id:
            self.current_estimate_id.action_submit()

    def action_estimate_generate_quotation(self):
        self.ensure_one()
        if self.current_estimate_id:
            return self.current_estimate_id.action_generate_quotation()

    # =========================================================================
    # STAGE CHANGE → AUTO-CREATE ESTIMATE
    # =========================================================================
    def write(self, vals):
        if 'stage_id' in vals:
            estimating_stage = self.env.ref(
                'patriot_crm.stage_estimating', raise_if_not_found=False)
            if estimating_stage and vals['stage_id'] == estimating_stage.id:
                res = super(CrmLead, self).write(vals)
                self._create_auto_estimate()
                return res
        return super(CrmLead, self).write(vals)

    def _create_auto_estimate(self):
        Estimate = self.env['ps.estimate']
        for lead in self:
            existing = Estimate.search([
                ('opportunity_id', '=', lead.id),
                ('state', '!=', 'lost')
            ], limit=1)
            if existing:
                _logger.info(f"Estimate already exists for lead {lead.name}")
                continue
            _logger.info(f"Auto-creating estimate for lead {lead.name}")
            est = Estimate.create({
                'opportunity_id': lead.id,
                'gc_partner_id': lead.gc_partner_id.id if lead.gc_partner_id else False,
            })
            est.action_populate_from_sign_types()
