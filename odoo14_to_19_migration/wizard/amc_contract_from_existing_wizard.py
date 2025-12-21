# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = __import__('logging').getLogger(__name__)


class AMCContractFromExistingWizard(models.TransientModel):
    """Wizard for creating migration records from existing AMC contracts"""
    _name = 'amc.contract.from.existing.wizard'
    _description = 'Import AMC Contracts from Existing Contracts'

    contract_ids = fields.Many2many(
        'amc.contract',
        string='Contracts to Migrate',
        required=True,
        help='Select existing AMC contracts to create migration records'
    )

    def action_create_migration_records(self):
        """Create migration line records from selected contracts"""
        self.ensure_one()
        
        if not self.contract_ids:
            raise UserError('Please select at least one contract to migrate.')
        
        MigrationLine = self.env['amc.contract.migration.line']
        created_count = 0
        skipped_count = 0
        
        # Check which contracts already have migration records
        existing_numbers = set()
        contract_numbers = self.contract_ids.mapped('name')
        existing_records = MigrationLine.search([('contract_number', 'in', contract_numbers)])
        existing_numbers = set(existing_records.mapped('contract_number'))
        
        # Create migration lines
        lines_to_create = []
        for contract in self.contract_ids:
            # Skip if migration record already exists
            if contract.name in existing_numbers:
                skipped_count += 1
                continue
            
            # Get customer name
            customer_name = contract.customer_id.name if contract.customer_id else ''
            
            # Get stage name (status)
            status_name = contract.stage_id.name if contract.stage_id else ''
            
            # Get branch ID from company (if we can map it back)
            # Note: We need to get the odoo14_branch_id from the branch mapping
            branch_id = None
            if contract.branch_id:
                # Try to find the odoo14_branch_id from the mapping
                mapping = self.env['odoo14.branch.company.mapping'].search([
                    ('odoo19_company_id', '=', contract.branch_id.id),
                    ('active', '=', True)
                ], limit=1)
                if mapping:
                    branch_id = mapping.odoo14_branch_id
            
            lines_to_create.append({
                'contract_number': contract.name or f'Contract-{contract.id}',
                'start_date': contract.start_date,
                'end_date': contract.end_date,
                'customer_name': customer_name,
                'contract_value': contract.contract_value or 0.0,
                'status_name': status_name,
                'contract_date': contract.contract_date,
                'odoo14_branch_id': branch_id,
                'status': 'pending_migration',
                'status_message': 'Created from existing contract',
            })
            created_count += 1
        
        # Batch create all records
        if lines_to_create:
            MigrationLine.create(lines_to_create)
            self.env.cr.commit()
        
        # Return action to show created records
        message = f'Created {created_count} migration record(s)'
        if skipped_count > 0:
            message += f', skipped {skipped_count} (already exist)'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Migration Records Created',
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

