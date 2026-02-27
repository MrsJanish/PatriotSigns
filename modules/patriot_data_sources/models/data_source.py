from odoo import models, fields


class DataSource(models.Model):
    _name = 'ps.data.source'
    _description = 'Data Source'
    _order = 'name'

    name = fields.Char('Name', required=True)
    description = fields.Text('Description')
    field_ids = fields.Many2many(
        'ps.data.source.field',
        'ps_data_source_field_rel',
        'source_id',
        'field_id',
        string='Fields',
    )
    field_count = fields.Integer(
        'Field Count',
        compute='_compute_field_count',
    )

    def _compute_field_count(self):
        for rec in self:
            rec.field_count = len(rec.field_ids)


class DataSourceField(models.Model):
    _name = 'ps.data.source.field'
    _description = 'Data Source Field'
    _order = 'name'

    name = fields.Char('Field Name', required=True)
    model_name = fields.Char('Model')
    technical_name = fields.Char('Technical Name')
    data_source_ids = fields.Many2many(
        'ps.data.source',
        'ps_data_source_field_rel',
        'field_id',
        'source_id',
        string='Data Sources',
    )
