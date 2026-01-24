# -*- coding: utf-8 -*-
###############################################################################
#
#    Equdai
#
#    Copyright (C) 2024-TODAY Equdai(<https://equdai.ae>)
#    Author: Equdai (odoo@equdai.ae)
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
###############################################################################
from odoo import api, fields, models


class IrAttachment(models.Model):
    """Inherit IR attachment for adding extra fields and inheriting create
    function """
    _inherit = 'ir.attachment'

    attach_to = fields.Selection([('project', 'Project'),
                                  ('task', 'Task')],
                                 required=True, string="Attach To",
                                 help="if Project, file attached to Project."
                                      " Otherwise to task.", default='project')
    project_id = fields.Many2one('project.project',
                                 string='Project',
                                 help="This indicates the Project",
                                 readonly="True")
    task_id = fields.Many2one('project.task',
                              string='Task', help="This indicates the Task",
                              readonly="True")

    @api.model_create_multi
    def create(self, vals_list):
        """Supering the create function inorder to add the project and task
         corresponding to the attachment"""
        for vals in vals_list:
            res_model = vals.get('res_model')
            res_id = vals.get('res_id')
            project_id = vals.get('project_id')
            task_id = vals.get('task_id')

            if project_id and not task_id:
                vals['res_id'] = project_id
                vals['res_model'] = 'project.project'
            elif project_id and task_id:
                vals['res_id'] = task_id
                vals['res_model'] = 'project.task'
            elif not project_id and res_model == 'project.project' and res_id:
                vals['project_id'] = res_id
                vals['attach_to'] = 'project'
            elif not task_id and res_model == 'project.task' and res_id:
                vals['task_id'] = res_id
                vals['attach_to'] = 'task'

            # New logic to ensure project_id consistency when res_model is project.task
            if vals.get('project_id') and vals.get('res_model') == 'project.task' and vals.get('res_id'):
                task = self.env['project.task'].browse(vals['res_id'])
                if task.project_id.id != vals['project_id']:
                    vals['project_id'] = task.project_id.id
            elif not vals.get('project_id') and vals.get('res_model') == 'project.task' and vals.get('res_id'):
                task = self.env['project.task'].browse(vals['res_id'])
                vals['project_id'] = task.project_id.id

        return super().create(vals_list)
