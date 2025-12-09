from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError


class SalesRevision(models.Model):
    _inherit = 'sale.order'

    revision_id = fields.Many2one('sale.order.revision', string='Revision Group', copy=False)
    revision_number = fields.Char(string='Revision Number', copy=False)
    revision_count = fields.Integer(string='Revisions', compute='_compute_revision_count')
    is_completed = fields.Boolean(string="Completed", default=True)

    @api.depends('revision_id')
    def _compute_revision_count(self):
        for record in self:
            if record.revision_id:
                record.revision_count = self.env['sale.order'].search_count([('revision_id', '=', record.revision_id.id)])
            else:
                record.revision_count = 0

    def create_new_version(self):
        revision_id = self.revision_id
        if not revision_id:
            vals = {
                'name': self.name,
                'last_code': 0
            }
            revision_id = self.env['sale.order.revision'].create(vals)
            self.write({
                'revision_id': revision_id.id
            })

        try:
            action = self.env['ir.actions.act_window']._for_xml_id('eq_saleorder_revision.action_revision_wizard_sale_order')
        except ValueError:
            # Fallback if XML ID not found (module needs upgrade)
            action = self.env.ref('eq_saleorder_revision.action_revision_wizard_sale_order').sudo().read()[0]
        action['context'] = dict(
            self.env.context,
            default_order_id=self.id,
            default_revision_id=revision_id.id,
            default_next_code=revision_id.last_code + 1
        )
        return action

    def action_view_revisions(self):
        sale_orders = self.env['sale.order'].search([('revision_id', '=', self.revision_id.id)])

        try:
            result = self.env['ir.actions.act_window']._for_xml_id('eq_saleorder_revision.action_view_revised_quote')
        except ValueError:
            # Fallback if XML ID not found (module needs upgrade)
            result = self.env.ref('eq_saleorder_revision.action_view_revised_quote').sudo().read()[0]
        result['domain'] = [('id', 'in', sale_orders.ids)]
        return result

    def action_confirm(self):
        if self.revision_id:
            sale_orders = self.env['sale.order'].search([('revision_id', '=', self.revision_id.id)])
            for rec in sale_orders:
                if rec.id != self.id:
                    rec.is_completed = False
            self.is_completed = True
        return super(SalesRevision, self).action_confirm()


class SaleOrderGroup(models.Model):
    _name = 'sale.order.revision'
    _description = 'Sale Order Revision Group'

    name = fields.Char(string='Name', required=True)
    last_code = fields.Integer(string='Last Code')
