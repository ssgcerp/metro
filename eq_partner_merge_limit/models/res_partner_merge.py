from odoo import models, api, _
from odoo.exceptions import UserError
import sys
import importlib


class BasePartnerMergeAutomaticWizard(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    @api.model
    def _get_merge_limit(self):
        """Return the merge limit - override to change from default 3"""
        return 20

    def action_merge(self):
        """Override action_merge to increase limit from 3 to 20"""
        # Get partner IDs from the wizard
        if hasattr(self, 'partner_ids'):
            partner_ids = self.partner_ids.ids
        elif hasattr(self, 'partner_to_merge_ids'):
            partner_ids = self.partner_to_merge_ids.ids
        else:
            partner_ids = []
        
        merge_limit = self._get_merge_limit()
        
        # Check if partner_ids exceed our custom limit
        if len(partner_ids) > merge_limit:
            raise UserError(_(
                'For safety reasons, you cannot merge more than %d contacts together. '
                'You can re-open the wizard several times if needed.'
            ) % merge_limit)
        
        # Call parent method
        return super().action_merge()

    def _merge(self, partner_ids, dst_partner=None):
        """Override _merge method to increase limit from 3 to 20"""
        merge_limit = self._get_merge_limit()
        
        # Check if partner_ids exceed our custom limit
        if len(partner_ids) > merge_limit:
            raise UserError(_(
                'For safety reasons, you cannot merge more than %d contacts together. '
                'You can re-open the wizard several times if needed.'
            ) % merge_limit)
        
        # Call parent method
        return super()._merge(partner_ids, dst_partner=dst_partner)


# Also try to override MAX_MERGE_PARTNERS constant if it exists
def _override_constant():
    """Try to override MAX_MERGE_PARTNERS constant"""
    possible_paths = [
        'odoo.addons.base.wizard.res_partner_merge_wizard',
        'odoo.addons.base.models.res_partner_merge',
        'odoo.addons.base_partner_merge.wizard.base_partner_merge',
    ]
    
    for path in possible_paths:
        try:
            module = importlib.import_module(path)
            if hasattr(module, 'MAX_MERGE_PARTNERS'):
                module.MAX_MERGE_PARTNERS = 20
                break
        except (ImportError, AttributeError, ModuleNotFoundError):
            continue

# Try to override constant when module loads
try:
    _override_constant()
except Exception:
    pass

