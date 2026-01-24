# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def find_duplicates(self):
        """
        Find duplicate partners based on name (case-insensitive, trimmed).
        Only active partners, exclude child contacts (parent_id IS NULL).
        Returns groups with 2 or more partners.
        """
        # Get all active partners without parent (main contacts only)
        partners = self.search([
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

        # Filter groups with 2+ partners
        duplicate_groups = []
        for normalized_name, partner_list in duplicates_dict.items():
            if len(partner_list) >= 2:
                duplicate_groups.append({
                    'name': normalized_name,
                    'partners': partner_list,
                    'count': len(partner_list),
                })

        return duplicate_groups

