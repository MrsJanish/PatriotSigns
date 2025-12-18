from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    x_patriot_theme = fields.Selection([
        ('clean', 'Clean (Default)'),
        ('aurora', 'Aurora (Dark Mode)')
    ], string="Patriot Theme", default='clean', required=True)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['x_patriot_theme']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['x_patriot_theme']
