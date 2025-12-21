# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SignType(models.Model):
    """
    Sign Type model - represents a type of sign (e.g., SN-1, Room ID, ADA).
    Each sign type belongs to an opportunity and can have multiple bookmarks
    linking to locations in the PDF drawings.
    """
    _name = 'cc.sign.type'
    _description = 'Sign Type'
    _order = 'name'

    name = fields.Char(
        string='Sign Type ID',
        required=True,
        help='Sign type identifier, e.g., SN-1, RID-1, ADA-1'
    )
    opportunity_id = fields.Many2one(
        'cc.opportunity',
        string='Opportunity',
        required=True,
        ondelete='cascade'
    )
    description = fields.Text(
        string='Description',
        help='Full description of this sign type'
    )
    quantity = fields.Integer(
        string='Quantity',
        default=1,
        help='Number of signs of this type'
    )
    dimensions = fields.Char(
        string='Dimensions',
        help='Size of the sign, e.g., 24" x 36"'
    )
    material = fields.Char(
        string='Material',
        help='Sign material, e.g., Aluminum, Acrylic'
    )
    mounting = fields.Char(
        string='Mounting',
        help='Mounting method, e.g., Wall, Post, Ceiling'
    )
    color = fields.Char(
        string='Color/Finish',
        help='Sign color or finish'
    )
    notes = fields.Text(
        string='Notes',
        help='Additional notes about this sign type'
    )
    
    # Relationship to bookmarks
    bookmark_ids = fields.One2many(
        'cc.sign.bookmark',
        'sign_type_id',
        string='Bookmarks'
    )
    bookmark_count = fields.Integer(
        string='Bookmarks',
        compute='_compute_bookmark_count'
    )
    
    # Status
    confirmed = fields.Boolean(
        string='Confirmed',
        default=False,
        help='Set to true when sign type is confirmed for the schedule'
    )
    
    @api.depends('bookmark_ids')
    def _compute_bookmark_count(self):
        for record in self:
            record.bookmark_count = len(record.bookmark_ids)
    
    def action_view_bookmarks(self):
        """Open PDF viewer at the first bookmark for this sign type"""
        self.ensure_one()
        if self.bookmark_ids:
            first_bookmark = self.bookmark_ids[0]
            return {
                'type': 'ir.actions.client',
                'tag': 'cc_ops_pdf_viewer',
                'params': {
                    'attachmentId': first_bookmark.attachment_id.id,
                    'opportunityId': self.opportunity_id.id,
                    'goToPage': first_bookmark.page_number,
                }
            }
        return {'type': 'ir.actions.act_window_close'}


class SignBookmark(models.Model):
    """
    Sign Bookmark model - links a sign type to a specific location in a PDF.
    Stores page number and click coordinates for rendering highlights.
    """
    _name = 'cc.sign.bookmark'
    _description = 'Sign Bookmark'
    _order = 'page_number, id'

    sign_type_id = fields.Many2one(
        'cc.sign.type',
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
    highlight_color = fields.Char(
        string='Highlight Color',
        default='#f59e0b'
    )
    path_data = fields.Text(
        string='Lasso Path',
        help='JSON array of {x, y} normalized coordinates forming the lasso region'
    )
    note = fields.Char(
        string='Note',
        help='Optional note about this bookmark'
    )
    
    # Computed fields for display
    opportunity_id = fields.Many2one(
        related='sign_type_id.opportunity_id',
        store=True
    )
    attachment_name = fields.Char(
        related='attachment_id.name',
        string='Document Name'
    )
    
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
            }
        }
