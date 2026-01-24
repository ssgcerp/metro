from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class PurchaseRequisitionApprovalWizard(models.TransientModel):
    _name = 'purchase.requisition.approval.wizard'
    _description = 'Purchase Requisition Approval Wizard'

    remark = fields.Text(string='Remark', required=True)
    requisition_id = fields.Many2one('purchase.requisition', string='Requisition')

    @api.model
    def default_get(self, fields):
        res = super(PurchaseRequisitionApprovalWizard, self).default_get(fields)
        active_id = self._context.get('active_id')
        if active_id:
            res['requisition_id'] = active_id
        return res
    
    def action_approve(self):
        self.ensure_one()
        if not self.remark:
            raise UserError("Remark is required to approve the requisition.")

        requisition_id = self.requisition_id.id
        approval_stages = self.env['material.requisition.approver.stage'].search([
            ('requisition_id', '=', requisition_id),
            ('status', '=', '0'),  # Assuming '0' is the status for requesting approval
            ('visible_flag', '=', True),  # Assuming '1' is the visible flag indicating the first approver
        ])

        _logger.info("approval_stages")
        _logger.info(approval_stages)
        if not approval_stages:
            raise UserError("No approval stages found for this requisition.")

        # Update all found approval stages
        approval_stages.write({
            'status': '1',  # Change status to Approved
            'remark': self.remark,
            'approved_time': fields.Datetime.now(),  # Set approved time using fields module
        })

        last_approved_stage = self.env['material.requisition.approver.stage'].search([
            ('requisition_id', '=', requisition_id),
            ('status', '=', '1'),  
            ('visible_flag', '=', True) 
        ], order='id desc', limit=1)
        _logger.info("last_approved_stage")
        _logger.info(last_approved_stage)
        # If last_approved_stage is found, find the next stage
        if last_approved_stage:
            next_approval_stage = self.env['material.requisition.approver.stage'].search([
                ('requisition_id', '=', requisition_id),
                ('id', '>', last_approved_stage.id),  # Find next stage after last approved stage
                ('status', '=', '0'),  # Assuming '0' is the status for requesting approval
                ('visible_flag', '=', False)  # Assuming visible_flag indicates visibility
            ], limit=1)
            _logger.info("next_approval_stage")
            _logger.info(next_approval_stage)

            if next_approval_stage:
                next_approval_stage.write({
                    'visible_flag': True  # Set visible flag for next approver
                })

        return {'type': 'ir.actions.act_window_close'}

    def action_decline(self):
        self.ensure_one()
        if not self.remark:
            raise UserError("Remark is required to decline the requisition.")
        
        requisition_id = self.requisition_id.id
        approval_stages = self.env['material.requisition.approver.stage'].search([
            ('requisition_id', '=', requisition_id),
            ('status', '=', '0')
        ])

        if not approval_stages:
            raise UserError("No approval stages found for this requisition.")

        # Update all found approval stages to Declined status
        approval_stages.write({
            'status': '3',  # Change status to Declined
            'remark': self.remark,
            'approved_time': fields.Datetime.now(),  # Set declined time using fields module
        })

        decline_stage = self.env['stage.master'].search([('name', '=', 'Request Declined')])
        approval_stage = self.env['stage.master'].search([('name', '=', 'Request Approval')])
        if not decline_stage.exists():
                decline_stage = self.env['project.project.stage'].create({
                    'name': 'Request Declined',
                    'sequence': 11,
                })
        if not approval_stage.exists():
                approval_stage = self.env['project.project.stage'].create({
                    'name': 'Request Approval',
                    'sequence': 11,
                })
        context = dict(self._context or {})
        active_model = context.get('active_model')

        vals = {
                'date': datetime.now(),
                'from_stage': approval_stage.id,
                'to_stage': decline_stage.id,
                'remark': self.remark,
                'res_id': requisition_id,
                'model': active_model,
            }
        self.env['mail.messages'].create(vals)
        
        requisition = self.env['purchase.requisition'].browse(requisition_id)
        requisition.write({'state': 'decline','stage_id':decline_stage.id})

        return {'type': 'ir.actions.act_window_close'}


    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
    
   
