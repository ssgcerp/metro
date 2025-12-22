# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class EQFCRFQStage(models.Model):
    _name = 'eq.fc.rfq.stage'
    _description = 'EQ FC RFQ Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10, required=True, help='Order of stages')
    fold = fields.Boolean(string='Folded in Kanban', default=False, help='RFQs in this stage are folded in the kanban view')
    is_default = fields.Boolean(string='Is Default Stage', default=False, help='Default stages that cannot be deleted')
    is_approved_stage = fields.Boolean(string='Approved Stage', default=False, help='RFQ number is generated at this stage')
    is_locked_stage = fields.Boolean(string='Locked Stage', default=False, help='Mark this stage as locked. RFQs in locked stages cannot be modified.')
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
            
            # Check if any purchase order is using this stage (if we add stage_id to purchase.order later)
            # For now, just prevent deletion of default stages
            # purchase_orders = self.env['purchase.order'].search([('rfq_stage_id', '=', stage.id)])
            # if purchase_orders:
            #     raise UserError(f'Cannot delete stage "{stage.name}" because it is being used by {len(purchase_orders)} RFQ(s). Please change the stage of these RFQs first.')
        
        return super(EQFCRFQStage, self).unlink()

    def write(self, vals):
        """Allow modification of default stages except certain protected fields"""
        # Allow reordering of default stages
        protected_fields = ['is_default']  # Keep is_default protected
        if self.is_default and any(field in vals for field in protected_fields if field != 'sequence'):
            # Allow sequence changes for reordering
            if 'sequence' not in vals:
                raise UserError('Some fields of default stages cannot be modified! You can only reorder them by changing the sequence.')
        return super(EQFCRFQStage, self).write(vals)

