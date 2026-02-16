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
        'ps.estimate',
        'opportunity_id',
        string='Estimates',
    )
    estimate_count = fields.Integer(
        string='Estimates',
        compute='_compute_estimate_count',
    )
    # Flattened view of all estimate lines across all estimates for this lead
    estimate_line_ids = fields.One2many(
        'ps.estimate.line',
        compute='_compute_estimate_line_ids',
        string='Estimate Lines',
    )
    # Expose first estimate's header fields on the lead
    current_estimate_id = fields.Many2one(
        'ps.estimate',
        compute='_compute_current_estimate',
        string='Current Estimate',
    )
    estimate_state = fields.Selection(
        related='current_estimate_id.state',
        string='Estimate Status',
        readonly=True,
    )
    estimate_total = fields.Float(
        related='current_estimate_id.total',
        string='Estimate Total',
        readonly=True,
    )
    estimate_profit_margin_pct = fields.Float(
        related='current_estimate_id.profit_margin_pct',
        string='Estimate Margin %',
        readonly=True,
    )

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
        """Get the primary (most recent active) estimate"""
        for lead in self:
            active = lead.estimate_ids.filtered(lambda e: e.state != 'lost')
            lead.current_estimate_id = active[:1] if active else False

    def action_open_lead_or_estimate(self):
        """
        Called when clicking a kanban card in the pipeline.
        If the lead has estimates → open the estimate form directly.
        Otherwise → open the normal lead form.
        """
        self.ensure_one()
        if self.estimate_count > 0:
            # Redirect to the estimate form
            return self.action_view_estimates()
        # Default: open the lead form
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
        }

    def action_view_estimates(self):
        """Open linked estimates using the real Estimates action for proper menu context"""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'patriot_estimating.ps_estimate_action'
        )
        action['domain'] = [('opportunity_id', '=', self.id)]
        action['context'] = {'default_opportunity_id': self.id}
        if self.estimate_count == 1:
            action['view_mode'] = 'form'
            action['views'] = [(False, 'form')]
            action['res_id'] = self.estimate_ids[0].id
        return action

    def write(self, vals):
        # Look for stage change in 'vals' dictionary
        if 'stage_id' in vals:
            # Resolve the Estimating stage ID
            estimating_stage = self.env.ref('patriot_crm.stage_estimating', raise_if_not_found=False)
            
            # If changing TO global Estimating stage
            if estimating_stage and vals['stage_id'] == estimating_stage.id:
                res = super(CrmLead, self).write(vals)
                self._create_auto_estimate()
                return res
        
        return super(CrmLead, self).write(vals)

    def _create_auto_estimate(self):
        """Auto-create estimate when moving to Estimating stage"""
        Estimate = self.env['ps.estimate']
        
        for lead in self:
            # Check if any active estimate already exists
            existing = Estimate.search([
                ('opportunity_id', '=', lead.id),
                ('state', '!=', 'lost')  # Ignore lost estimates
            ], limit=1)
            
            if existing:
                _logger.info(f"Estimate already exists for lead {lead.name}, skipping auto-create.")
                continue
                
            _logger.info(f"Auto-creating estimate for lead {lead.name}")
            
            # Create the estimate header
            est = Estimate.create({
                'opportunity_id': lead.id,
                'gc_partner_id': lead.gc_partner_id.id if lead.gc_partner_id else False,
            })
            
            # Auto-populate lines from sign types
            est.action_populate_from_sign_types()
