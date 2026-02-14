from odoo import models, fields, api, _

class PartnerStatementReportHandler(models.AbstractModel):
    _name = 'partner.statement.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Partner Statement Report Handler'

    def _get_custom_display_config(self):
        return {
            'components': {
                'AccountReportFilters': {
                    'search_bar': True,
                    'partner': True,
                },
            }
        }

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        # Default options if needed
        options.setdefault('filter_partner', True)

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        return [(0, line) for line in self._get_partner_statement_lines(options)]

    def _get_partner_statement_lines(self, options):
        lines = []
        
        # If line_id is specified in options (drill down) behavior is handled by `account.report` usually via `unfold_all` or specific calls.
        # But wait, `_get_lines` is expected to return ALL lines or Top Level?
        # Typically Top Level.
        
        # If we want standard hierarchical behavior, we return top lines.
        
        context = self.env.context
        
        # Check if we are expanding a line
        # options.get('unfolded_lines') contains IDs of unfolded lines.
        
        # Using the logic from previous attempt
        
        # If no partner selected, we should show something or nothing?
        # Typically "No Data" if filter is required but empty.
        # But "Partner Ledger" shows all partners with balance if empty.
        
        domain = []
        if options.get('partner_ids'):
            domain.append(('id', 'in', options['partner_ids']))
        else:
            # If no partner filter, find partners with open balance in the period generally?
            # Or just return empty to force user to select?
            # User expectation: "Trial Balance" shows all. "Partner Ledger" shows all with balance.
            # Let's show partners with posted entries in the period.
            pass

        # Optimized search for partners with activity
        if not options.get('partner_ids'):
            # Find partners with moves in period using _read_group
            domain = [
                 ('parent_state', '=', 'posted'),
                 ('date', '<=', options['date']['date_to']),
                 ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable'))
            ]
            # Group by partner
            # _read_group returns (partner, )
            groups = self.env['account.move.line']._read_group(domain, groupby=['partner_id'], limit=100)
            partner_ids = [g[0].id for g in groups if g[0]]
            domain = [('id', 'in', partner_ids)]
             
        partners = self.env['res.partner'].search(domain)
        
        # Columns definition is in the Report Record, but we need to match values.
        
        for partner in partners:
             balance = self._get_partner_balance(partner, options)
             partner_line_id = f'partner~res.partner~{partner.id}'
             
             partner_line = {
                 'id': partner_line_id,
                 'name': partner.name,
                 'level': 2,
                 'unfoldable': True,
                 'unfolded': partner_line_id in options.get('unfolded_lines', []),
                 'columns': [
                     {'name': ''}, # Date
                     {'name': ''}, # Journal
                     {'name': ''}, # Ref
                     {'name': ''}, # Label
                     {'name': ''}, # Due Date
                     {'name': ''}, # Amount Curr
                     {'name': ''}, # Debit
                     {'name': ''}, # Credit
                     {'name': balance, 'class': 'number fw-bold'}, # Balance
                 ],
             }
             lines.append(partner_line)
             
             if partner_line['unfolded']:
                 lines.extend(self._get_partner_lines(options, partner.id, partner_line_id))
                 
        return lines

    def _get_partner_balance(self, partner, options):
        date_to = options['date']['date_to']
        domain = [
            ('partner_id', '=', partner.id),
            ('parent_state', '=', 'posted'),
            ('date', '<=', date_to),
            ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable'))
        ]
        # Use _read_group to sum
        result = self.env['account.move.line']._read_group(domain, aggregates=['debit:sum', 'credit:sum'])
        debit, credit = result[0]
        return (debit or 0.0) - (credit or 0.0)

    def _get_partner_lines(self, options, partner_id, parent_line_id):
        lines = []
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        
        opening_balance = self._get_opening_balance(partner_id, date_from)
        
        # Use a markup 'opening' but point to res.partner model to be safe, or account.move.line?
        # Model is used for actions. 'res.partner' is fine.
        lines.append({
            'id': f'opening~res.partner~{partner_id}', 
            'name': _("Opening Balance"),
            'level': 4,
            'parent_id': parent_line_id,
            'columns': [
                {'name': ''}, {'name': ''}, {'name': ''}, {'name': ''}, 
                {'name': ''}, {'name': ''}, {'name': ''}, {'name': ''},
                {'name': opening_balance, 'class': 'number'},
            ],
        })
        
        running_balance = opening_balance
        
        domain = [
            ('partner_id', '=', partner_id),
            ('parent_state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable'))
        ]
        
        move_lines = self.env['account.move.line'].search(domain, order='date, move_name')
        
        for line in move_lines:
            balance = line.debit - line.credit
            running_balance += balance
            
            lines.append({
                'id': f'line~account.move.line~{line.id}', # Standard ID
                'name': line.date.strftime('%Y-%m-%d'),
                'level': 4,
                'parent_id': parent_line_id,
                'caret_options': 'account.move.line',
                'columns': [
                    {'name': line.journal_id.code},
                    {'name': line.move_name},
                    {'name': line.name[:50] if line.name else ''},
                    {'name': line.date_maturity or ''},
                    {'name': line.amount_currency if line.currency_id != self.env.company.currency_id else ''},
                    {'name': line.debit},
                    {'name': line.credit},
                    {'name': running_balance, 'class': 'number'},
                ],
            })
        return lines

    def _get_opening_balance(self, partner_id, date_from):
        domain = [
            ('partner_id', '=', partner_id),
            ('parent_state', '=', 'posted'),
            ('date', '<', date_from),
            ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable'))
        ]
        result = self.env['account.move.line']._read_group(domain, aggregates=['debit:sum', 'credit:sum'])
        debit, credit = result[0]
        return (debit or 0.0) - (credit or 0.0)

    def _caret_options_initializer(self):
        # return map of 'caret_options' => dictionary of actions
        return {
            'account.move.line': [
                {'name': _("View Journal Entry"), 'action': 'open_document'},
            ]
        }
