from odoo import fields, models


class DefinedLocations(models.Model):
    """Location records linked to CRM leads and projects.

    Originally created via Odoo Studio.  Declared here so the module
    is self-contained on fresh databases.
    """
    _name = 'x_defined_locations'
    _description = 'Defined Locations'

    x_name = fields.Char('Location', required=True)
    x_studio_project = fields.Many2one('crm.lead', string='CRM Lead', ondelete='set null')
    x_studio_project_won = fields.Many2one('project.project', string='Project', ondelete='set null')
