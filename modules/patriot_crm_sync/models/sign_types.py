from odoo import fields, models


class SignTypes(models.Model):
    """Sign type records linked to CRM leads and projects.

    Originally created via Odoo Studio.  Declared here so the module
    is self-contained on fresh databases.
    """
    _name = 'x_sign_types'
    _description = 'Sign Types'

    x_name = fields.Char('Sign Type', required=True)
    x_studio_quantity = fields.Integer('Quantity')
    x_studio_category = fields.Char('Category')
    x_studio_project = fields.Many2one('crm.lead', string='CRM Lead', ondelete='set null')
    x_studio_generated_project = fields.Many2one('project.project', string='Project', ondelete='set null')
