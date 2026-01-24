# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
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
        """Prevent deletion of default stages and stages that are in use, unless it's a duplicate"""
        for stage in self:
            # Allow deletion if there's another stage with the same name (duplicate)
            duplicate_check = self.search([
                ('name', '=', stage.name),
                ('id', '!=', stage.id),
                ('active', 'in', [True, False])  # Check both active and inactive
            ])
            
            # If it's a default stage and NOT a duplicate, prevent deletion
            if stage.is_default and not duplicate_check:
                raise UserError('Default stages cannot be deleted! If you need to delete this stage, make sure there is another stage with the same name first.')
            
            # Check if any purchase order is using this stage
            purchase_orders = self.env['purchase.order'].search([('rfq_stage_id', '=', stage.id)])
            if purchase_orders and not duplicate_check:
                # If there's a duplicate, reassign to the other stage
                if duplicate_check:
                    other_stage = duplicate_check[0]
                    purchase_orders.write({'rfq_stage_id': other_stage.id})
                else:
                    raise UserError(f'Cannot delete stage "{stage.name}" because it is being used by {len(purchase_orders)} RFQ(s). Please change the stage of these RFQs first.')
            elif purchase_orders and duplicate_check:
                # Reassign to the duplicate (keeping the first one)
                other_stage = duplicate_check[0]
                purchase_orders.write({'rfq_stage_id': other_stage.id})
        
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
    
    @api.model
    def cleanup_duplicates(self):
        """Remove duplicate RFQ stages, keeping only the first one by ID and reassigning purchase orders"""
        # Get all stages grouped by name
        stages_by_name = {}
        all_stages = self.search([])
        
        for stage in all_stages:
            if stage.name not in stages_by_name:
                stages_by_name[stage.name] = []
            stages_by_name[stage.name].append(stage)
        
        # Find and handle duplicates
        duplicates_to_delete = []
        deleted_count = 0
        
        for stage_name, stages in stages_by_name.items():
            if len(stages) > 1:
                # Sort by ID to keep the first one (oldest)
                stages_sorted = sorted(stages, key=lambda s: s.id)
                keep_stage = stages_sorted[0]
                duplicate_stages = stages_sorted[1:]
                
                # Check if any purchase orders use the duplicate stages
                for dup_stage in duplicate_stages:
                    # Check if any purchase orders reference this duplicate stage
                    pos_with_dup = self.env['purchase.order'].search([
                        ('rfq_stage_id', '=', dup_stage.id)
                    ])
                    
                    if pos_with_dup:
                        # Reassign purchase orders to the stage we're keeping
                        pos_with_dup.write({
                            'rfq_stage_id': keep_stage.id
                        })
                    
                    # Temporarily set is_default to False to allow deletion
                    if dup_stage.is_default:
                        dup_stage.write({'is_default': False})
                    
                    duplicates_to_delete.append(dup_stage.id)
        
        # Delete duplicates
        if duplicates_to_delete:
            duplicates_records = self.browse(duplicates_to_delete)
            duplicates_records.unlink()
            deleted_count = len(duplicates_to_delete)
        
        return deleted_count

