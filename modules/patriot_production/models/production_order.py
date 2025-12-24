# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductionOrder(models.Model):
    """
    Production Order - Sign production batch.
    
    Groups sign instances for production scheduling.
    Links to MRP manufacturing orders.
    """
    _name = 'ps.production.order'
    _description = 'Sign Production Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'planned_date, id'

    # =========================================================================
    # IDENTIFICATION
    # =========================================================================
    name = fields.Char(
        string='Production Order',
        required=True,
        tracking=True
    )
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        ondelete='cascade'
    )
    
    # =========================================================================
    # SCHEDULING
    # =========================================================================
    planned_date = fields.Date(
        string='Planned Start',
        tracking=True
    )
    due_date = fields.Date(
        string='Due Date',
        tracking=True
    )
    actual_start_date = fields.Datetime(
        string='Actual Start'
    )
    actual_end_date = fields.Datetime(
        string='Actual End'
    )
    
    # =========================================================================
    # SIGN INSTANCES
    # =========================================================================
    instance_ids = fields.Many2many(
        'ps.sign.instance',
        'ps_production_instance_rel',
        'production_id',
        'instance_id',
        string='Sign Instances'
    )
    instance_count = fields.Integer(
        string='Signs',
        compute='_compute_instance_count'
    )
    
    # =========================================================================
    # MRP LINK
    # =========================================================================
    mrp_production_ids = fields.One2many(
        'mrp.production',
        'ps_production_order_id',
        string='Manufacturing Orders'
    )
    mrp_count = fields.Integer(
        string='MO Count',
        compute='_compute_mrp_count'
    )
    
    # =========================================================================
    # WORK TRACKING
    # =========================================================================
    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Current Workcenter'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('design', 'In Design'),
        ('fabrication', 'Fabrication'),
        ('assembly', 'Assembly'),
        ('qc', 'Quality Check'),
        ('complete', 'Complete'),
        ('shipped', 'Shipped'),
    ], string='Status', default='draft', tracking=True)
    
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='0')
    
    # =========================================================================
    # NOTES
    # =========================================================================
    notes = fields.Text(
        string='Production Notes'
    )

    # =========================================================================
    # COMPUTED
    # =========================================================================
    
    @api.depends('instance_ids')
    def _compute_instance_count(self):
        for order in self:
            order.instance_count = len(order.instance_ids)

    @api.depends('mrp_production_ids')
    def _compute_mrp_count(self):
        for order in self:
            order.mrp_count = len(order.mrp_production_ids)

    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def action_schedule(self):
        """Schedule for production"""
        self.write({'state': 'scheduled'})

    def action_start_design(self):
        """Move to design stage"""
        self.write({
            'state': 'design',
            'actual_start_date': fields.Datetime.now(),
        })

    def action_start_fabrication(self):
        """Move to fabrication"""
        self.write({'state': 'fabrication'})

    def action_start_assembly(self):
        """Move to assembly"""
        self.write({'state': 'assembly'})

    def action_start_qc(self):
        """Move to QC"""
        self.write({'state': 'qc'})

    def action_complete(self):
        """Mark complete"""
        self.write({
            'state': 'complete',
            'actual_end_date': fields.Datetime.now(),
        })
        # Update instance states
        self.instance_ids.write({'state': 'production'})

    def action_view_manufacturing_orders(self):
        """View linked MRP orders"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Manufacturing Orders - {self.name}',
            'res_model': 'mrp.production',
            'view_mode': 'list,form',
            'domain': [('ps_production_order_id', '=', self.id)],
            'context': {'default_ps_production_order_id': self.id},
        }

    def action_ship(self):
        """Mark as shipped and create installation"""
        for order in self:
            order.write({'state': 'shipped'})
            # Update project stage
            if order.project_id:
                order.project_id.write({'project_stage': 'shipping'})
            # Create installation record
            order._create_installation()
        
    def _create_installation(self):
        """Create installation record when production ships"""
        self.ensure_one()
        Installation = self.env.get('ps.installation')
        if not Installation:
            return False
        
        # Check if installation already exists
        existing = Installation.search([
            ('project_id', '=', self.project_id.id)
        ], limit=1)
        if existing:
            return existing
        
        # Calculate install date (1 week from now by default)
        from datetime import timedelta
        install_date = fields.Date.today() + timedelta(days=7)
        
        installation = Installation.create({
            'name': f"INST-{self.project_id.name}",
            'project_id': self.project_id.id,
            'scheduled_date': install_date,
            'instance_ids': [(6, 0, self.instance_ids.ids)] if self.instance_ids else [],
            'state': 'scheduled',
        })
        return installation



class QualityCheck(models.Model):
    """
    Quality Check - QC checkpoint for production.
    """
    _name = 'ps.quality.check'
    _description = 'Quality Check'
    _order = 'check_date desc'

    production_order_id = fields.Many2one(
        'ps.production.order',
        string='Production Order',
        required=True,
        ondelete='cascade'
    )
    instance_id = fields.Many2one(
        'ps.sign.instance',
        string='Sign Instance'
    )
    
    # Check details
    check_type = fields.Selection([
        ('visual', 'Visual Inspection'),
        ('dimension', 'Dimension Check'),
        ('color', 'Color Match'),
        ('braille', 'Braille Verification'),
        ('assembly', 'Assembly Check'),
        ('final', 'Final Inspection'),
    ], string='Check Type', required=True)
    
    check_date = fields.Datetime(
        string='Check Date',
        default=fields.Datetime.now
    )
    checked_by = fields.Many2one(
        'res.users',
        string='Checked By',
        default=lambda self: self.env.user
    )
    
    # Result
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('rework', 'Needs Rework'),
    ], string='Result', required=True)
    
    notes = fields.Text(
        string='Notes'
    )
    
    # Photo evidence
    photo_ids = fields.Many2many(
        'ir.attachment',
        string='Photos'
    )
