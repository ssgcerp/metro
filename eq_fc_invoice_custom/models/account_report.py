from odoo import models, fields, api, _

class AccountReport(models.Model):
    _inherit = 'account.report'

    def _get_options(self, previous_options=None):
        options = super()._get_options(previous_options)
        
        # Target specific report: 'l10n_ae.tax_report'
        # We can also check by external ID if needed, or stick to this check if robust.
        # To be safe, let's check the XML ID lookup or cache it.
        uae_tax_report = self.env.ref('l10n_ae.tax_report', raise_if_not_found=False)
        
        if uae_tax_report and self.id == uae_tax_report.id:
            # Check context for multiple companies
            allowed_company_ids = self.env.context.get('allowed_company_ids', [])
            
            # Only enable if multiple companies are selected in the environment
            if len(allowed_company_ids) > 1:
                # 1. Prepare the Dropdown Options
                # Get all allowed companies
                companies = self.env['res.company'].browse(allowed_company_ids)
                
                # Check if a specific company was selected in previous options
                current_specific_id = (previous_options or {}).get('specific_company_id')
                
                # If selected, ensure it's still valid (in allowed companies)
                if current_specific_id and int(current_specific_id) not in allowed_company_ids:
                    current_specific_id = None

                # Build the options list for the UI
                specific_company_filter = []
                # Add "All" option (default behavior)
                specific_company_filter.append({
                    'id': 'all',
                    'name': _('All Companies'),
                    'selected': not current_specific_id
                })
                
                for c in companies:
                    is_selected = str(c.id) == str(current_specific_id) if current_specific_id else False
                    specific_company_filter.append({
                        'id': c.id,
                        'name': c.name,
                        'selected': is_selected
                    })

                options['specific_company_filter'] = specific_company_filter
                options['specific_company_id'] = current_specific_id

                # 2. Spoof the Report Scope if a company is selected
                if current_specific_id:
                    target_company_id = int(current_specific_id)
                    # Force the report to only look at this company
                    # 'company_ids' determines the scope for queries
                    options['company_ids'] = [target_company_id]
                    # 'multi_company' determines the UI for standard selector (optional to touch)
                    # We leave multi_company as is, or updated to reflect reality?
                    # If we update 'company_ids', the report engine should respect it.
                    
                    # Also need to ensure 'multi_company_creation_date' logic doesn't break?
                    # Generally safely sticking to 'company_ids' is enough for queries.

        return options
