# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class AMCContractStage(models.Model):
    _name = 'amc.contract.stage'
    _description = 'AMC Contract Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10, required=True, help='Order of stages')
    fold = fields.Boolean(string='Folded in Kanban', default=False, help='Contracts in this stage are folded in the kanban view')
    is_default = fields.Boolean(string='Is Default Stage', default=False, help='Default stages that cannot be deleted')
    is_confirmed_stage = fields.Boolean(string='Confirmed Stage', default=False, help='Contract number is generated when reaching this stage')
    is_cancelled_stage = fields.Boolean(string='Cancelled Stage', default=False, help='Mark this stage as a cancelled stage. Multiple stages can be marked as cancelled.')
    active = fields.Boolean(string='Active', default=True)
    color = fields.Integer(string='Color', default=0, help='Color used in kanban view')
    
    description = fields.Text(string='Description', help='Description of the stage')
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Stage name must be unique!'),
    ]

    def unlink(self):
        """Prevent deletion of default stages and stages that are in use"""
        for stage in self:
            if stage.is_default:
                raise UserError('Default stages cannot be deleted!')
            
            # Check if any contract is using this stage
            contracts = self.env['amc.contract'].search([('stage_id', '=', stage.id)])
            if contracts:
                raise UserError(f'Cannot delete stage "{stage.name}" because it is being used by {len(contracts)} contract(s). Please change the stage of these contracts first.')
        
        return super(AMCContractStage, self).unlink()

    def write(self, vals):
        """Allow modification of default stages except certain protected fields"""
        # Allow reordering of default stages
        protected_fields = ['is_default']  # Keep is_default protected
        if self.is_default and any(field in vals for field in protected_fields if field != 'sequence'):
            # Allow sequence changes for reordering
            if 'sequence' not in vals:
                raise UserError('Some fields of default stages cannot be modified! You can only reorder them by changing the sequence.')
        return super(AMCContractStage, self).write(vals)

