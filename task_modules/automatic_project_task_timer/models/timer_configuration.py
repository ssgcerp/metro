# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Mohammed Irfan T(odoo@cybrosys.com)
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


class TimerConfiguration(models.Model):
    """Timer configuration model for configuring the automatic timer
    stage activation. Each project has different stages,
    based on the configured stages for each project, the timer will run."""
    _name = 'timer.configuration'
    _description = 'Timer Configuration'

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        help='Configure the project to activate the timer'
    )
    stage_ids = fields.Many2many(
        'project.task.type',
        string='Stages',
        help='Select multiple stages to activate the timer'
    )

    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Set the domain for stage_ids field to select the stages
        from the stages of the selected project"""
        if self.project_id:
            self.stage_ids = self.env['project.task.type'].search([
                ('project_ids', 'in', self.project_id.id)
            ])

    @api.model
    def create(self, vals):
        """To set the status stage for all the tasks in the corresponding
        project, so that the warning message will pop-ups when the form
        opens. For that supering the ORM Create method to get the corresponding
         project. """
        projects = self.env['project.project'].sudo().browse(vals.get(
            'project_id'))
        tasks = self.env['project.task'].search([('project_id', '=' ,projects.id)])
        for records in tasks:
            stage_ids = vals.get('stage_ids', [(6, 0, [])])[-1]  # Extracting the list of stage IDs
            if isinstance(stage_ids, list) and records.stage_id.id in stage_ids:
                records.write({'is_status_stage': True})
            else:
                records.write({'is_status_stage': False})
        res = super(TimerConfiguration, self).create(vals)
        return res
