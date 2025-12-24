# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    """
    Partner extensions for sign industry contacts.
    
    Adds classification flags for:
    - General Contractors
    - Building Owners/Clients
    - Architects
    - Sign Suppliers
    """
    _inherit = 'res.partner'

    # === Industry Classification ===
    is_gc = fields.Boolean(
        string='Is General Contractor',
        default=False,
        help='Check if this partner is a General Contractor'
    )
    is_owner = fields.Boolean(
        string='Is Owner/Client',
        default=False,
        help='Check if this partner is a building owner or client'
    )
    is_architect = fields.Boolean(
        string='Is Architect',
        default=False,
        help='Check if this partner is an architect or design firm'
    )
    is_sign_supplier = fields.Boolean(
        string='Is Sign Supplier',
        default=False,
        help='Check if this partner is a sign supplier (e.g., Omega)'
    )
    
    # === External System IDs ===
    construct_connect_id = fields.Char(
        string='ConstructConnect ID',
        help='ID in ConstructConnect system for this company'
    )
    
    # === Supplier-specific fields ===
    supplier_alias = fields.Char(
        string='Supplier Alias',
        help='Short alias for supplier (e.g., "Omega")'
    )
    supplier_lead_time = fields.Integer(
        string='Lead Time (days)',
        help='Typical lead time in business days'
    )
    
    # === GC-specific fields ===
    gc_prequalified = fields.Boolean(
        string='Prequalified',
        default=False,
        help='GC has been prequalified for bidding'
    )
    default_payment_terms = fields.Char(
        string='Typical Payment Terms',
        help='Typical payment terms for this GC'
    )
