from odoo import models, fields


class DataSource(models.Model):
    _name = 'x_data_source'
    _description = 'Data Source'
    _order = 'x_name'

    x_name = fields.Char('Name', required=True)
    x_description = fields.Text('Description')
    x_field_ids = fields.Many2many(
        'x_data_source_field',
        'x_data_source_field_rel',
        'source_id',
        'field_id',
        string='Fields',
    )
    x_field_count = fields.Integer(
        'Field Count',
        compute='_compute_field_count',
    )

    def _compute_field_count(self):
        for rec in self:
            rec.x_field_count = len(rec.x_field_ids)


class DataSourceField(models.Model):
    _name = 'x_data_source_field'
    _description = 'Data Source Field'
    _order = 'x_name'

    x_name = fields.Char('Field Name', required=True)
    x_model_name = fields.Char('Model')
    x_technical_name = fields.Char('Technical Name')
    x_data_source_ids = fields.Many2many(
        'x_data_source',
        'x_data_source_field_rel',
        'field_id',
        'source_id',
        string='Data Sources',
    )
