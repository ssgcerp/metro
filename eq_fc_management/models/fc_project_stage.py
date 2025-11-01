# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class FCProjectStage(models.Model):
    _name = 'fc.project.stage'
    _description = 'Project Stage for Financial Control'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10, help='Order of stages')
    fold = fields.Boolean(string='Folded in Kanban', default=False, help='Projects in this stage are folded in the kanban view')
    is_default = fields.Boolean(string='Is Default Stage', default=False, help='Default stages that cannot be deleted')
    is_confirmed_stage = fields.Boolean(string='Confirmed Stage', default=False, help='Project code is generated when reaching this stage')
    active = fields.Boolean(string='Active', default=True)
    color = fields.Integer(string='Color', default=0, help='Color used in kanban view')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    description = fields.Text(string='Description', help='Description of the stage')
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Stage name must be unique!'),
    ]

    def unlink(self):
        """Prevent deletion of default stages and stages that are in use"""
        for stage in self:
            if stage.is_default:
                raise UserError('Default stages cannot be deleted!')
            
            # Check if any project is using this stage
            projects = self.env['project.project'].search([('stage_id', '=', stage.id)])
            if projects:
                raise UserError(f'Cannot delete stage "{stage.name}" because it is being used by {len(projects)} project(s). Please change the stage of these projects first.')
        
        return super(FCProjectStage, self).unlink()

    def write(self, vals):
        """Prevent modification of certain fields for default stages"""
        if self.is_default and any(field in vals for field in ['name', 'sequence', 'is_confirmed_stage']):
            raise UserError('Default stages cannot be modified!')
        return super(FCProjectStage, self).write(vals)
