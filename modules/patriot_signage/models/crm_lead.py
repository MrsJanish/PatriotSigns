# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CrmLead(models.Model):
    """
    Extend CRM Lead with sign type relationship.
    
    This extension is in patriot_signage (not patriot_crm) because
    sign_type_ids references ps.sign.type which is defined in this module.
    """
    _inherit = 'crm.lead'

    # Sign Schedule Summary
    sign_type_ids = fields.One2many(
        'ps.sign.type',
        'opportunity_id',
        string='Sign Types'
    )
    sign_type_count = fields.Integer(
        string='Sign Types',
        compute='_compute_sign_counts',
        store=True
    )
    total_sign_quantity = fields.Integer(
        string='Total Signs',
        compute='_compute_sign_counts',
        store=True
    )

    @api.depends('sign_type_ids', 'sign_type_ids.quantity')
    def _compute_sign_counts(self):
        for lead in self:
            lead.sign_type_count = len(lead.sign_type_ids)
            lead.total_sign_quantity = sum(lead.sign_type_ids.mapped('quantity'))
