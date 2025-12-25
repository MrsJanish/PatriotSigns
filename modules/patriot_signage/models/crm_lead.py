# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CrmLead(models.Model):
    """
    Extend CRM Lead with sign type relationship and profitability tracking.
    
    Billing rates go into BID PRICE.
    Actual labor costs (from HR employee.hourly_cost) come out of PROFIT.
    """
    _inherit = 'crm.lead'

    # =========================================================================
    # SIGN SCHEDULE
    # =========================================================================
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

    # =========================================================================
    # PROJECT PROFITABILITY - BID SIDE
    # =========================================================================
    
    total_bid_price = fields.Float(
        string='Total Bid Price',
        compute='_compute_project_profitability',
        store=True,
        help='Signs + Shop Labor + Install Labor (billing rates) + Travel + Equipment'
    )
    
    # Shop labor - estimated hours for bidding
    shop_hours = fields.Float(
        string='Shop Hours',
        help='Estimated hours for shop production'
    )
    shop_labor_billed = fields.Float(
        string='Shop Labor Billed',
        compute='_compute_project_profitability',
        store=True,
        help='Shop hours × $75/hr billing rate'
    )
    
    # Install labor - uses installer_hourly_rate from patriot_crm
    install_labor_billed = fields.Float(
        string='Install Labor Billed',
        compute='_compute_project_profitability',
        store=True,
        help='Install hours × installer billing rate ($25/$15/$40)'
    )

    # =========================================================================
    # PROJECT PROFITABILITY - COST SIDE
    # =========================================================================
    
    total_material_cost = fields.Float(
        string='Material Cost',
        compute='_compute_project_profitability',
        store=True,
        help='Sum of extended costs from sign types'
    )
    total_labor_cost = fields.Float(
        string='Labor Cost',
        compute='_compute_project_profitability',
        store=True,
        help='Actual labor from timesheets (hours × employee hourly_cost from HR)'
    )
    total_project_cost = fields.Float(
        string='Total Project Cost',
        compute='_compute_project_profitability',
        store=True,
        help='Materials + Actual Labor + Travel + Equipment'
    )
    
    # PROFIT
    total_profit = fields.Float(
        string='Total Profit',
        compute='_compute_project_profitability',
        store=True,
        help='Bid Price - Total Cost'
    )
    project_margin_pct = fields.Float(
        string='Profit Margin %',
        compute='_compute_project_profitability',
        store=True,
        help='Profit as percentage of bid price'
    )

    # =========================================================================
    # TIMESHEET TRACKING (actual labor from HR)
    # =========================================================================
    timesheet_hours = fields.Float(
        string='Timesheet Hours',
        compute='_compute_timesheet_totals',
        help='Total hours logged to linked project'
    )
    timesheet_cost = fields.Float(
        string='Timesheet Cost',
        compute='_compute_timesheet_totals',
        help='Actual cost from timesheets (hours × employee hourly_cost from HR)'
    )

    # =========================================================================
    # BILLING RATES
    # =========================================================================
    SHOP_BILLING_RATE = 75.0  # $/hr - shop labor billing rate

    # =========================================================================
    # COMPUTED METHODS
    # =========================================================================
    
    @api.depends('sign_type_ids', 'sign_type_ids.quantity')
    def _compute_sign_counts(self):
        for lead in self:
            lead.sign_type_count = len(lead.sign_type_ids)
            lead.total_sign_quantity = sum(lead.sign_type_ids.mapped('quantity'))

    def _compute_timesheet_totals(self):
        """
        Compute timesheet hours and ACTUAL cost from linked project.
        Cost = each timesheet line's hours × that employee's hourly_cost from HR.
        
        Note: This gracefully handles the case where patriot_projects is not installed
        or the opportunity_id field doesn't exist on project.project.
        """
        Project = self.env['project.project']
        Timesheet = self.env['account.analytic.line']
        
        # Check if opportunity_id field exists on project.project
        has_opportunity_link = 'opportunity_id' in Project._fields
        
        for lead in self:
            if has_opportunity_link:
                try:
                    project = Project.search([('opportunity_id', '=', lead.id)], limit=1)
                    if project:
                        timesheets = Timesheet.search([('project_id', '=', project.id)])
                        lead.timesheet_hours = sum(timesheets.mapped('unit_amount'))
                        
                        # Actual cost from HR employee hourly_cost
                        total_cost = 0
                        for ts in timesheets:
                            if ts.employee_id and ts.employee_id.hourly_cost:
                                total_cost += ts.unit_amount * ts.employee_id.hourly_cost
                        lead.timesheet_cost = total_cost
                    else:
                        lead.timesheet_hours = 0
                        lead.timesheet_cost = 0
                except Exception:
                    lead.timesheet_hours = 0
                    lead.timesheet_cost = 0
            else:
                lead.timesheet_hours = 0
                lead.timesheet_cost = 0

    @api.depends(
        'sign_type_ids.extended_price',
        'sign_type_ids.extended_cost',
        'shop_hours',
        'estimated_install_hours',
        'installer_hourly_rate',
        'travel_cost',
        'equipment_rental_cost'
    )
    def _compute_project_profitability(self):
        """
        BID PRICE (billing rates):
          - Sign prices
          - Shop labor × $75/hr
          - Install labor × installer billing rate ($25/$15/$40)
          - Travel + Equipment
        
        COST (actual from HR):
          - Sign costs  
          - Timesheet hours × employee hourly_cost (from HR)
          - Travel + Equipment
        
        PROFIT = BID - COST
        """
        for lead in self:
            # === SIGNS ===
            signs_price = sum(lead.sign_type_ids.mapped('extended_price'))
            signs_cost = sum(lead.sign_type_ids.mapped('extended_cost'))
            
            # === SHOP LABOR BILLING ===
            shop_hrs = lead.shop_hours or 0
            lead.shop_labor_billed = shop_hrs * self.SHOP_BILLING_RATE
            
            # === INSTALL LABOR BILLING ===
            # Uses installer_hourly_rate from patriot_crm ($25/$15/$40 based on crew)
            install_hrs = lead.estimated_install_hours or 0
            install_billing_rate = lead.installer_hourly_rate or 40.0
            lead.install_labor_billed = install_hrs * install_billing_rate
            
            # === PASS-THROUGH ===
            travel = lead.travel_cost or 0
            equipment = lead.equipment_rental_cost or 0
            
            # === TOTALS ===
            lead.total_bid_price = (
                signs_price + 
                lead.shop_labor_billed + 
                lead.install_labor_billed + 
                travel + 
                equipment
            )
            
            # Cost uses ACTUAL labor from HR via timesheets
            lead.total_material_cost = signs_cost
            lead.total_labor_cost = lead.timesheet_cost
            lead.total_project_cost = signs_cost + lead.timesheet_cost + travel + equipment
            
            # === PROFIT ===
            lead.total_profit = lead.total_bid_price - lead.total_project_cost
            
            if lead.total_bid_price:
                lead.project_margin_pct = (lead.total_profit / lead.total_bid_price) * 100
            else:
                lead.project_margin_pct = 0
