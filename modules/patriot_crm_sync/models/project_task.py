from odoo import fields, models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    x_studio_project_bid = fields.Many2one(
        'crm.lead', string='Linked CRM Lead', ondelete='set null',
    )
