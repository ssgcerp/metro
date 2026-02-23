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
    is_draft_stage = fields.Boolean(string='Draft Stage', default=False, help='Mark this stage as a draft stage. Used for behaviors that require identifying draft stages.')
    allow_confirm_action = fields.Boolean(string='Allow Confirm Button', default=False, help='Show the Confirm action button when a project is in this stage.')
    allow_next_action = fields.Boolean(string='Allow Next Button', default=True, help='Show the Next action button when a project is in this stage.')
    allow_cancel_action = fields.Boolean(string='Allow Cancel Button', default=False, help='Show the Cancel action button when a project is in this stage.')
    is_completed_stage = fields.Boolean(string='Completed Stage', default=False, help='Mark this stage as a completed stage.')
    is_cancel_stage = fields.Boolean(string='Cancellation Stage', default=False, help='Stage representing a cancelled project.')
    sms_template_id = fields.Many2one('sms.template', string='SMS Template', help='Template to send SMS notifications when project reaches this stage')
    mail_template_id = fields.Many2one('mail.template', string='Email Template', domain=[('model', '=', 'project.project')], help="If set, an email will be sent to the customer when the project reaches this step.")
    active = fields.Boolean(string='Active', default=True)
    color = fields.Integer(string='Color', default=0, help='Color used in kanban view')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    description = fields.Text(string='Description', help='Description of the stage')
    
    # Alias fields to comply with expected API names (no behavior change)
    allow_next_button = fields.Boolean(related='allow_next_action', string='Allow Next Button', store=True, readonly=False)
    allow_confirm_button = fields.Boolean(related='allow_confirm_action', string='Allow Confirm Button', store=True, readonly=False)
    allow_cancel_button = fields.Boolean(related='allow_cancel_action', string='Allow Cancel Button', store=True, readonly=False)
    confirmed_stage = fields.Boolean(related='is_confirmed_stage', string='Confirmed Stage', store=True, readonly=False)
    completed_stage = fields.Boolean(related='is_completed_stage', string='Completed Stage', store=True, readonly=False)
    cancellation_stage = fields.Boolean(related='is_cancel_stage', string='Cancellation Stage', store=True, readonly=False)
    draft_stage = fields.Boolean(related='is_draft_stage', string='Draft Stage', store=True, readonly=False)

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
