# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PartnerMergeWizard(models.TransientModel):
    _name = 'eq.partner.merge.wizard'
    _description = 'Partner Duplicate Merge Wizard'

    duplicate_name = fields.Char(
        string='Duplicate Name',
        readonly=True,
        required=True,
    )
    partner_ids = fields.Many2many(
        'res.partner',
        string='Partners to Merge',
        readonly=True,
        required=True,
    )
    primary_partner_id = fields.Many2one(
        'res.partner',
        string='Primary Partner',
        required=False,
        domain="[('id', 'in', partner_ids)]",
        help='Select the partner that will be kept. All other partners will be merged into this one.',
    )
    partner_count = fields.Integer(
        string='Partner Count',
        compute='_compute_partner_count',
        store=False,
    )
    @api.depends('partner_ids')
    def _compute_partner_count(self):
        """Compute the number of partners in the duplicate group."""
        for wizard in self:
            wizard.partner_count = len(wizard.partner_ids)

    @api.constrains('partner_ids', 'primary_partner_id')
    def _check_partners(self):
        """Validate partner selection."""
        for wizard in self:
            if len(wizard.partner_ids) < 2:
                raise ValidationError(_('You must select at least 2 partners to merge.'))
            if len(wizard.partner_ids) > 10:
                raise ValidationError(_('Maximum 10 partners can be merged at once.'))
            if wizard.primary_partner_id and wizard.primary_partner_id not in wizard.partner_ids:
                raise ValidationError(_('Primary partner must be selected from the partners list.'))

    def _check_merge_safety(self, partners):
        """
        Check if merge is safe to perform.
        Raises UserError if merge should be blocked.
        """
        # Check for different companies (excluding False/None)
        companies = partners.mapped('company_id').filtered(lambda c: c)
        if len(companies) > 1:
            raise UserError(_(
                'Cannot merge partners from different companies: %s'
            ) % ', '.join(companies.mapped('name')))

        # Check for active users
        partners_with_users = partners.filtered(lambda p: p.user_ids)
        if partners_with_users:
            raise UserError(_(
                'Cannot merge partners with active users attached: %s'
            ) % ', '.join(partners_with_users.mapped('name')))

    def _reassign_references(self, primary_partner, partners_to_merge):
        """
        Reassign all references from partners_to_merge to primary_partner.
        Uses ORM methods, not raw SQL.
        """
        # Account Moves (Invoices)
        if 'account.move' in self.env:
            moves = self.env['account.move'].search([
                ('partner_id', 'in', partners_to_merge.ids)
            ])
            moves.write({'partner_id': primary_partner.id})

        # Sale Orders
        if 'sale.order' in self.env:
            sale_orders = self.env['sale.order'].search([
                ('partner_id', 'in', partners_to_merge.ids)
            ])
            sale_orders.write({'partner_id': primary_partner.id})

        # Purchase Orders
        if 'purchase.order' in self.env:
            purchase_orders = self.env['purchase.order'].search([
                ('partner_id', 'in', partners_to_merge.ids)
            ])
            purchase_orders.write({'partner_id': primary_partner.id})

        # CRM Leads
        if 'crm.lead' in self.env:
            leads = self.env['crm.lead'].search([
                ('partner_id', 'in', partners_to_merge.ids)
            ])
            leads.write({'partner_id': primary_partner.id})

        # Mail Followers
        followers = self.env['mail.followers'].search([
            ('res_model', '=', 'res.partner'),
            ('res_id', 'in', partners_to_merge.ids)
        ])
        # Remove duplicate followers first
        existing_followers = self.env['mail.followers'].search([
            ('res_model', '=', 'res.partner'),
            ('res_id', '=', primary_partner.id)
        ])
        existing_partner_ids = existing_followers.mapped('partner_id').ids
        for follower in followers:
            if follower.partner_id.id not in existing_partner_ids:
                follower.write({'res_id': primary_partner.id})
            else:
                follower.unlink()

        # Mail Messages
        messages = self.env['mail.message'].search([
            ('model', '=', 'res.partner'),
            ('res_id', 'in', partners_to_merge.ids)
        ])
        messages.write({'res_id': primary_partner.id})

        # Partner Bank Accounts
        bank_accounts = self.env['res.partner.bank'].search([
            ('partner_id', 'in', partners_to_merge.ids)
        ])
        bank_accounts.write({'partner_id': primary_partner.id})

    def _merge_categories(self, primary_partner, partners_to_merge):
        """Merge category tags from merged partners to primary partner."""
        all_categories = partners_to_merge.mapped('category_id')
        primary_categories = primary_partner.category_id
        new_categories = all_categories - primary_categories
        if new_categories:
            primary_partner.write({
                'category_id': [(4, cat.id) for cat in new_categories]
            })

    def _merge_child_contacts(self, primary_partner, partners_to_merge):
        """Merge child contacts from merged partners to primary partner."""
        child_contacts = self.env['res.partner'].search([
            ('parent_id', 'in', partners_to_merge.ids)
        ])
        child_contacts.write({'parent_id': primary_partner.id})

    def _log_merge_in_chatter(self, primary_partner, partners_to_merge):
        """Log merge operation in primary partner's chatter."""
        merged_names = ', '.join(partners_to_merge.mapped('name'))
        message = _(
            'Merged partners into this record: %s'
        ) % merged_names
        primary_partner.message_post(body=message)

    def action_merge_partners(self):
        """
        Main merge action.
        Validates, reassigns references, merges data, and archives partners.
        """
        self.ensure_one()

        # Validation
        if len(self.partner_ids) < 2:
            raise UserError(_('You must select at least 2 partners to merge.'))
        if len(self.partner_ids) > 10:
            raise UserError(_('Maximum 10 partners can be merged at once.'))
        if not self.primary_partner_id:
            raise UserError(_('You must select a primary partner.'))
        if self.primary_partner_id not in self.partner_ids:
            raise UserError(_('Primary partner must be selected from the partners list.'))

        # Get partners to merge (excluding primary)
        partners_to_merge = self.partner_ids - self.primary_partner_id
        primary_partner = self.primary_partner_id

        # Safety checks
        all_partners = self.partner_ids
        self._check_merge_safety(all_partners)

        # Perform merge operations
        try:
            # Reassign references
            self._reassign_references(primary_partner, partners_to_merge)

            # Merge categories
            self._merge_categories(primary_partner, partners_to_merge)

            # Merge child contacts
            self._merge_child_contacts(primary_partner, partners_to_merge)

            # Log in chatter
            self._log_merge_in_chatter(primary_partner, partners_to_merge)

            # Archive merged partners (safe deletion)
            partners_to_merge.write({'active': False})

            # Return success message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _(
                        'Successfully merged %d partner(s) into %s.'
                    ) % (len(partners_to_merge), primary_partner.name),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Error during merge operation: %s') % str(e))

    def action_find_duplicates(self):
        """
        Find duplicates and populate the current wizard record.
        Called from the form view button.
        """
        self.ensure_one()
        Partner = self.env['res.partner']
        
        # Get all active partners without parent (main contacts only)
        partners = Partner.search([
            ('active', '=', True),
            ('parent_id', '=', False),
        ])

        # Group by normalized name
        duplicates_dict = {}
        for partner in partners:
            # Normalize name: trim and lowercase
            normalized_name = (partner.name or '').strip().lower()
            if normalized_name:
                if normalized_name not in duplicates_dict:
                    duplicates_dict[normalized_name] = []
                duplicates_dict[normalized_name].append(partner)

        # Count total duplicate groups
        total_groups = sum(1 for partner_list in duplicates_dict.values() if len(partner_list) >= 2)
        
        # Find first duplicate group with 2+ partners
        for normalized_name, partner_list in duplicates_dict.items():
            if len(partner_list) >= 2:
                # Populate current wizard record
                self.write({
                    'duplicate_name': partner_list[0].name,
                    'partner_ids': [(6, 0, [p.id for p in partner_list])],
                })
                # Set first partner as default primary
                if partner_list:
                    self.primary_partner_id = partner_list[0]
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Duplicates Found'),
                        'message': _('Found %d duplicate group(s). Showing first group with %d contacts. Please select the primary partner and click Merge Partners.') % (total_groups, len(partner_list)),
                        'type': 'success',
                        'sticky': False,
                    }
                }

        # No duplicates found
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('No Duplicates Found'),
                'message': _('No duplicate partners found.'),
                'type': 'info',
                'sticky': False,
            }
        }

    @api.model
    def find_and_create_duplicates(self):
        """
        Find all duplicate partners and create wizard records for each group.
        Returns action to refresh the view.
        """
        Partner = self.env['res.partner']
        
        # Clear existing wizard records first
        self.search([]).unlink()
        
        # Get all active partners without parent (main contacts only)
        partners = Partner.search([
            ('active', '=', True),
            ('parent_id', '=', False),
        ])

        # Group by normalized name
        duplicates_dict = {}
        for partner in partners:
            # Normalize name: trim and lowercase
            normalized_name = (partner.name or '').strip().lower()
            if normalized_name:
                if normalized_name not in duplicates_dict:
                    duplicates_dict[normalized_name] = []
                duplicates_dict[normalized_name].append(partner)

        # Filter groups with 2+ partners and create wizard records
        wizard_records = []
        for normalized_name, partner_list in duplicates_dict.items():
            if len(partner_list) >= 2:
                # Create wizard record for this duplicate group
                wizard_record = self.create({
                    'duplicate_name': partner_list[0].name,  # Use original name from first partner
                    'partner_ids': [(6, 0, [p.id for p in partner_list])],
                })
                wizard_records.append(wizard_record.id)

        # Show notification
        if not wizard_records:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Duplicates Found'),
                    'message': _('No duplicate partners found.'),
                    'type': 'info',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Duplicates Found'),
                    'message': _('Found %d duplicate group(s).') % len(wizard_records),
                    'type': 'success',
                    'sticky': False,
                }
            }

