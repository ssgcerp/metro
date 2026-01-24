# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Jumana Haseen (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

class ProjectApproval(models.Model):
    """This class creates a model 'project.approval' and adds
    required fields"""
    _name = 'project.approval'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Project Approval'

    name = fields.Char(default='Project Approval Configuration', string="Name",
                       help="Project Approval configuration.")
    approve_boq_project = fields.Boolean(string="Approval on "
                                                     "BOQ",
                                              help='Enable this field '
                                                   'for adding the approvals '
                                                   'for the BOQ.')
    boq_approver_ids = fields.Many2many('res.users',
                                            'boq_id',
                                            string='BOQ Approver',
                                            help='In this field you can add '
                                                 'the approvers for the '
                                                 'boq.')
    number_of_hours_for_auto_approval_boq = fields.Char(string="Number of Hours for Auto Approval",
                       help="Time in Hours waiting for auto approval")
    approve_material_requisition = fields.Boolean(string="Approval on "
                                                     "Material Requisition",
                                              help='Enable this field '
                                                   'for adding the approvals '
                                                   'for the Requisition.')
    # material_requisition_approver_ids = fields.Many2many(
    #     'res.groups', 
    #     'project_approval_res_groups_rel',  
    #     'project_approval_id',  
    #     'res_groups_id', 
    #     string='Approver Groups',
    #     domain="[('full_name', 'in', ['Project Admin', 'Project Manager', 'Technical Manager', 'Purchase Officer', 'Engineer','Purchase Manager'])]"
    # )
    number_of_hours_for_auto_approval_material_req = fields.Char(string="Number of Hours for Auto Approval",
                       help="Time in Hours waiting for auto approval")
    no_approve = fields.Boolean(string='No Approval',
                                help='Approval is not needed',
                                compute="_compute_no_approve")

    material_requisition_approver_ids = fields.One2many('project.approval.group', 'approval_id', string="Approval Groups")

    @api.depends('approve_boq_project')
    def _compute_no_approve(self):
        """Method _compute_no_approve to compute the value to the field
        no_approve"""
        for rec in self:
            rec.no_approve = True if rec.approve_boq_project else False

    @api.model
    def create(self, vals):
        res = super(ProjectApproval, self).create(vals)
        if 'material_requisition_approver_ids' in vals:
            self._update_sequence(res.material_requisition_approver_ids)
        return res

    def write(self, vals):
        res = super(ProjectApproval, self).write(vals)
        if 'material_requisition_approver_ids' in vals:
            self._update_sequence(self.material_requisition_approver_ids)
        return res

    def _update_sequence(self, approval_groups):
        sequence = 10
        for group in approval_groups:
            group.sequence = sequence
            sequence += 10

class StateMaster(models.Model):
    _inherit = 'stage.master'

   
    in_request = fields.Boolean(string='In Request', default=False)

    def stage_uniq(self):
        req_list = []

        stage_obj_in_request = self.env['stage.master'].search([('in_request', '=', True)])
        for stage in stage_obj_in_request:
            req_list.append(stage.id)
            if len(set(req_list)) > 1:
                return False

        return True

    _constraints = [
        (stage_uniq, 'In request state must be unique!',
         ['in_request'])
    ]

class ProjectApprovalGroup(models.Model):
    _name = 'project.approval.group'
    _description = 'Project Approval Groups'

    approval_id = fields.Many2one('project.approval', string="Approval")
    group_id = fields.Many2one('res.groups', string="Group",
        domain="[('full_name', 'in', ['Project Admin', 'Project Manager', 'Technical Manager', 'Purchase Officer', 'Engineer','Purchase Manager'])]"
                               )
    sequence = fields.Integer(string="Sequence")

    _sql_constraints = [
        ('unique_group_per_approval', 'unique(approval_id, group_id)', 'Group must be unique per approval!')
    ]
