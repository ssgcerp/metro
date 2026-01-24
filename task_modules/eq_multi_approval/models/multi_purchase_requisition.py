from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    approval_button_visible = fields.Boolean(compute='_compute_approval_button_visibility',
                                            string='Approval Button Visible',
                                            store=False,default=True)
    
    material_requisition_approver_ids = fields.One2many(
        'material.requisition.approver.stage',
        'requisition_id',
        string='Material Requisition Approvers'
    )

    @api.depends('material_requisition_approver_ids')
    def _compute_approval_button_visibility(self):
        current_user = self.env.user
        for requisition in self:
            visible_flag = True
            for approver_stage in requisition.material_requisition_approver_ids:
                if (approver_stage.approver_id and
                    current_user.id == approver_stage.approver_id.id and
                    approver_stage.status == '0' and
                    approver_stage.visible_flag):
                    visible_flag = False
                    break

            requisition.approval_button_visible = visible_flag

    def open_approval_wizard(self):
        self.ensure_one()
        approver_stages = self.env['material.requisition.approver.stage'].search([
            ('requisition_id', '=', self.id),
            ('visible_flag', '=', True)
        ])
        
        user_id = self.env.user.id
        
        # Find if current user belongs to any of the approver groups with visible_flag = True
        visible_approver_stage = False
        for stage in approver_stages:
            if stage.approver_id.id == user_id:
                visible_approver_stage = True
                break
        
        if not visible_approver_stage:
            raise UserError("You are not authorized to approve this requisition.")

        return {
            'name': 'Approve Requisition',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.requisition.approval.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'default_requisition_id': self.id,
            }
        }
