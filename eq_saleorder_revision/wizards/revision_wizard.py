from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError


class SalesRevision(models.TransientModel):
    _name = 'sale.order.revision.wizard'

    order_id = fields.Many2one('sale.order', string='Sale Order')
    revision_id = fields.Many2one('sale.order.revision', string='Revision Group')
    next_code = fields.Integer(string='Next Code')
    reason = fields.Char(string="Reason", required=True)

    def create_revision(self):
        sale_orders = self.env['sale.order'].search([('revision_id', '=', self.revision_id.id)])
        for rec in sale_orders:
            rec.is_completed = False
        vals = {
            'name': self.revision_id.name + ' R' + str(self.next_code),
            'state': 'draft',
            'revision_id': self.revision_id.id,
            'is_completed': True
        }
        copy_id = self.order_id.copy(default=vals)
        self.revision_id.write({
            'last_code': self.next_code
        })
        self.order_id.message_post(body=_("Revision: %s Reason: %s") % (self.next_code, self.reason))

        action = self.env['ir.actions.act_window']._for_xml_id('sale.action_quotations_with_onboarding')
        form_view = [(self.env.ref('sale.view_order_form').id, 'form')]
        action['views'] = form_view
        action['res_id'] = copy_id.id
        return action
