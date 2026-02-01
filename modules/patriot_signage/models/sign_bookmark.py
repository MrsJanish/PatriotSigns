# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SignBookmark(models.Model):
    """
    Sign Bookmark - Links a sign type to a specific location in a PDF document.
    
    Stores page number and coordinates for rendering highlights in the PDF viewer.
    Supports both point clicks and lasso-style region selections.
    """
    _name = 'ps.sign.bookmark'
    _description = 'Sign Bookmark'
    _order = 'page_number, id'

    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    sign_type_id = fields.Many2one(
        'ps.sign.type',
        string='Sign Type',
        required=True,
        ondelete='cascade'
    )
    attachment_id = fields.Many2one(
        'ir.attachment',
        string='PDF Document',
        required=True,
        ondelete='cascade'
    )
    
    # Computed references
    opportunity_id = fields.Many2one(
        related='sign_type_id.opportunity_id',
        string='Project',
        store=True
    )
    attachment_name = fields.Char(
        related='attachment_id.name',
        string='Document Name'
    )
    sign_type_name = fields.Char(
        related='sign_type_id.name',
        string='Sign Type Name'
    )

    # =========================================================================
    # POSITION
    # =========================================================================
    page_number = fields.Integer(
        string='Page Number',
        required=True,
        default=1
    )
    x_position = fields.Float(
        string='X Position',
        help='Horizontal position (0-1 ratio from left)'
    )
    y_position = fields.Float(
        string='Y Position',
        help='Vertical position (0-1 ratio from top)'
    )

    # =========================================================================
    # LASSO REGION
    # =========================================================================
    path_data = fields.Text(
        string='Lasso Path',
        help='JSON array of {x, y} normalized coordinates forming the lasso region'
    )
    has_lasso = fields.Boolean(
        string='Has Lasso',
        compute='_compute_has_lasso',
        store=True
    )

    # =========================================================================
    # DISPLAY
    # =========================================================================
    highlight_color = fields.Char(
        string='Highlight Color',
        default='#f59e0b'
    )
    note = fields.Char(
        string='Note',
        help='Optional note about this bookmark'
    )

    # =========================================================================
    # COMPUTED
    # =========================================================================
    
    @api.depends('path_data')
    def _compute_has_lasso(self):
        for record in self:
            record.has_lasso = bool(record.path_data)

    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def action_go_to_bookmark(self):
        """Open PDF viewer at this bookmark location"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'cc_ops_pdf_viewer',
            'params': {
                'attachmentId': self.attachment_id.id,
                'opportunityId': self.opportunity_id.id,
                'goToPage': self.page_number,
            },
        }
