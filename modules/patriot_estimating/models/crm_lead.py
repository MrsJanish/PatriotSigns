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

    @api.depends('estimate_ids')
    def _compute_estimate_count(self):
        for lead in self:
            lead.estimate_count = len(lead.estimate_ids)

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
                # We need to call super BEFORE creating estimate? 
                # Or AFTER? Logic doesn't depend on write, but safer to write first.
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
