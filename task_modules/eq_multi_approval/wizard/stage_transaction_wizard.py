# -*- coding: utf-8 -*-

from datetime import datetime
from odoo.tools.translate import _
from odoo import api, fields, models
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ApprovalWizard(models.TransientModel):
    _inherit = 'approval.wizard'
    _description = 'Approval Wizard'

    stage_domain = fields.Many2many('stage.master', compute='_compute_stage_domain', store=False, string='Stage Domain')

    @api.model
    def create(self, vals):
        rec = super(ApprovalWizard, self).create(vals)

        rec.onchange_current_stage()
        return rec

    @api.depends('current_stage')
    def _compute_stage_domain(self):
        for wizard in self:
            context = dict(wizard._context or {})
            active_model = context.get('active_model')
            _logger.info("active_model")
            _logger.info(active_model)

            stage_domain_ids = []

            if active_model == 'project.task':
                active_ids = context.get('active_ids')
                model_rec = self.env[active_model].browse(active_ids)
                
                for record in model_rec:
                    model_id = self.env['ir.model'].search([('model', '=', active_model)])
                    stage_obj = self.get_stagetransaction_record(record.stage_master_id.id, model_id.id) or []
                    stage_domain_ids = [stage.to_stage.id for stage in stage_obj]
            else:
                active_ids = context.get('active_ids')
                model_rec = self.env[active_model].browse(active_ids)
                _logger.info("model_rec")
                _logger.info(model_rec)

                for record in model_rec:
                    model_id = self.env['ir.model'].search([('model', '=', active_model)])
                    stage_obj = self.get_stagetransaction_record(record.stage_id.id, model_id.id) or []
                    stage_domain_ids = [stage.to_stage.id for stage in stage_obj]
                    _logger.info("stage_domain_ids")
                    _logger.info(stage_domain_ids)

            if not stage_domain_ids:
                all_stage_ids = self.env['stage.master'].search([]).ids
                wizard.stage_domain = [(6, 0, all_stage_ids)]
            else:
                wizard.stage_domain = [(6, 0, stage_domain_ids)]

    @api.onchange('current_stage')
    def onchange_current_stage(self):
        self._compute_stage_domain()
        stage_ids = self.stage_domain.ids
        _logger.info("stage_domain")
        _logger.info(stage_ids)
        if stage_ids:
            return {
                'domain': {
                    'new_stage': [('id', 'in', stage_ids)]
                }
            }
        else:
            return {
                'domain': {
                    'new_stage': [('id', 'in', [])]
                }
            }

    def get_stagetransaction_record(self, from_stage, model):
        user_obj = self.env['res.users']
        user_data = user_obj.browse(self._uid)
        user_groups = user_data.groups_id
        
        user = self.env.user  
        
        if user_groups:
            stage_objs = []
            for user_group in user_groups:
                stage_obj = self.env['stage.transaction'].search([
                    ('from_stage', '=', from_stage),
                    ('model', '=', model),
                    ('groups', '=', user_group.id)  
                ])
                if stage_obj:
                    stage_objs.append(stage_obj) 
            return stage_objs or False

    def update_status(self):
        context = dict(self._context or {})
        self = self.with_context(aprv=True)
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        app = self.env[active_model].browse(active_ids)
        _logger.info("fe_active_model")
        _logger.info(active_model)

        if self.current_stage and self.new_stage:
            new_stage_id = self.new_stage.id
            stage = self.env['project.project.stage'].browse(new_stage_id)
            if not stage.exists():
                stage = self.env['project.project.stage'].create({
                    'name': self.new_stage.name,
                    'sequence': 10,
                })
                new_stage_id = stage.id

            for approval in app:
                if self.new_stage.approved:
                    if active_model == 'project.task':
                        approval.stage_master_id = self.new_stage
                    else:
                        approval.stage_id = self.new_stage.id

                    vals = {
                        'date': datetime.now(),
                        'from_stage': self.current_stage.id,
                        'to_stage': self.new_stage.id,
                        'remark': self.remark,
                        'res_id': approval.id,
                        'model': active_model,
                    }

                    context.update({'copy': True})
                    approval.change_state(context)
                else:
                    if active_model == 'project.task':
                        approval.stage_master_id = self.new_stage
                    else:
                        approval.stage_id = self.new_stage.id

                    vals = {
                        'date': datetime.now(),
                        'from_stage': self.current_stage.id,
                        'to_stage': self.new_stage.id,
                        'remark': self.remark,
                        'res_id': approval.id,
                        'model': active_model,
                    }
                    context.update({'copy': False})
                    approval.change_state(context)

                self.env['mail.messages'].create(vals)
        else:
            raise UserError(_("Please select new_stage for transaction."))

        if active_model == 'purchase.requisition':
            requisition = self.env['purchase.requisition'].browse(approval.id)
            approval_stage = self.env['stage.master'].search([('name', '=', 'Request Approval')])
            if not approval_stage.exists():
                approval_stage = self.env['stage.master'].create({
                    'name': 'Request Approval',
                    'sequence': 11,
                })
            approved_stage = self.env['stage.master'].search([('approved', '=', True)])
            cancelled_stage = self.env['stage.master'].search([('foreclosed', '=',True)])
            if(approved_stage == self.new_stage):
                requisition.write({'state': 'confirm'})
            elif(cancelled_stage == self.new_stage):
                requisition.write({'state': 'cancel'})
            elif(approval_stage == self.new_stage):
                requisition.write({'state': 'request_approval'})
                project_approval = self.env['project.approval'].search([('approve_material_requisition', '=', True)], order='id desc', limit=1)
                _logger.info("project_approval")
                _logger.info(project_approval)
                if project_approval and project_approval.approve_material_requisition:
                    approvers = project_approval.material_requisition_approver_ids.mapped('group_id')
                    _logger.info("approvers")
                    _logger.info(approvers)
                    if approvers:
                            approvers = approvers[:-1]  # Exclude the last approver
                            for idx, approver in enumerate(approvers):
                                project = approval.project_id
                                # project = self.env['project.project'].browse(5)
                                _logger.info("project_idd")
                                _logger.info(project.id)
                                if hasattr(project, approver.name):
                                    field_value = getattr(project, approver.name)
                                    user_ids = []
                                    if approver.name == 'engineer' or approver.name == 'purchase_officer':
                                        user_ids = field_value.ids

                                    else:
                                        user_ids = [field_value.id]

                                    _logger.info("user_ids")
                                    _logger.info(user_ids)

                                    for user_id in user_ids:
                                        self.env['material.requisition.approver.stage'].create({
                                                'requisition_id': approval.id,
                                                'approver_id': user_id,
                                                'status': '0',
                                                'send_time': datetime.now(),
                                                'visible_flag': idx == 0  # True for the first approver, False for others
                                        })
            else:
                requisition.write({'state': 'draft'})
                
    def reset_status(self):
        context = dict(self._context or {})
        stage_obj = self.env['stage.master'].search([('draft', '=', True)])
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        app = self.env[active_model].browse(active_ids)
        for approval in app:
            approval.stage_id = stage_obj.id
            vals = {
                'date': datetime.now(),
                'from_stage': self.current_stage.id,
                'to_stage': stage_obj.id,
                'remark': self.remark,
                'res_id': approval.id,
                'model': active_model,
            }
            self.env['mail.messages'].create(vals)

    def change_state(self, approval, context):
        if context.get('copy'):
            # Logic for approved state
            if hasattr(approval, 'stage_master_id'):
                approval.stage_master_id = self.new_stage
            else:
                approval.stage_id = self.new_stage.id
        else:
            # Logic for non-approved state
            if hasattr(approval, 'stage_master_id'):
                approval.stage_master_id = self.new_stage
            else:
                approval.stage_id = self.new_stage.id
       
