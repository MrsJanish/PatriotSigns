from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    # Removed required=True to prevent potential SQL locking/default issues on upgrades
    x_patriot_theme = fields.Selection([
        ('clean', 'Clean (Default)'),
        ('aurora', 'Aurora (Dark Mode)')
    ], string="Patriot Theme", default='clean')

    # Commented out security overrides until system is stable
    # @property
    # def SELF_READABLE_FIELDS(self):
    #     return super().SELF_READABLE_FIELDS + ['x_patriot_theme']

    # @property
    # def SELF_WRITEABLE_FIELDS(self):
    #     return super().SELF_WRITEABLE_FIELDS + ['x_patriot_theme']
