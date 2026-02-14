# -*- coding: utf-8 -*-
from odoo import models, fields


class CrewEstimating(models.Model):
    """Extend ps.crew with billing rate for estimating."""
    _inherit = 'ps.crew'

    combined_rate = fields.Float(
        string='Combined Rate ($/hr)',
        help='Combined hourly billing rate for the full crew',
    )
