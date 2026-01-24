from odoo import fields, models


class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    is_retention_product = fields.Boolean(string="Retention Product")

