from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class ResCompany(models.Model):
    _inherit = 'res.company'

    soa_enable_auto_email = fields.Boolean(string='Enable Automatic Monthly Statements')
    soa_day_of_month = fields.Integer(string='Day of Month', default=1, help='Day of the month to send statements')
    soa_statement_type = fields.Selection([
        ('customer', 'Customers Only'),
        ('vendor', 'Vendors Only'),
        ('both', 'Both')
    ], string='Statement Type', default='customer')
    
    def _cron_send_match_partners(self):
        """
        Cron method to send statements.
        """
        today = fields.Date.today()
        day = today.day
        
        companies = self.search([
            ('soa_enable_auto_email', '=', True),
            ('soa_day_of_month', '=', day)
        ])
        
        for company in companies:
            company._send_monthly_statements()

    def _send_monthly_statements(self):
        """
        Send statements for this company.
        """
        self.ensure_one()
        # Determine partners
        domain = []
        if self.soa_statement_type == 'customer':
            domain = [('parent_id', '=', False), ('customer_rank', '>', 0)]
        elif self.soa_statement_type == 'vendor':
            domain = [('parent_id', '=', False), ('supplier_rank', '>', 0)]
        else:
            domain = [('parent_id', '=', False), '|', ('customer_rank', '>', 0), ('supplier_rank', '>', 0)]
            
        # Add filter for balance > 0? Requirement says "Configurable in settings" or "Filter: Only partners with balance > 0"
        # Let's assume we implement the balance check in the logic to avoid sending empty statements.
        
        candidates = self.env['res.partner'].search(domain)
        partners_to_send = self.env['res.partner']
        
        # Check balance. This can be slow if many partners. 
        # Using optimized query or just trusting account.move.line search
        # Ideally, we should search for partners with open moves.
        
        move_domain = [
            ('parent_state', '=', 'posted'),
            ('company_id', '=', self.id),
            ('amount_residual', '!=', 0),
            ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable'))
        ]
        
        # Get partners with open moves
        self.env.cr.execute(f"""
            SELECT DISTINCT partner_id 
            FROM account_move_line 
            WHERE parent_state = 'posted' 
              AND company_id = %s 
              AND amount_residual != 0
              AND account_id IN (
                  SELECT id FROM account_account WHERE account_type IN ('asset_receivable', 'liability_payable')
              )
        """, (self.id,))
        result = self.env.cr.fetchall()
        partner_ids_with_balance = [r[0] for r in result if r[0]]
        
        partners_to_send = candidates.filtered(lambda p: p.id in partner_ids_with_balance)
        
        if not partners_to_send:
            return

        # Prepare Wizard Data
        date_to = fields.Date.today()
        date_from = date_to.replace(day=1) # Start of current month? Or previous month?
        # Usually statements are sent for the *previous* month.
        # If running on Day 1, maybe for previous month.
        # If I run on 1st Feb, I want Jan 1 to Jan 31.
        
        last_month = date_to - relativedelta(months=1)
        date_from = last_month.replace(day=1)
        date_to_report = last_month + relativedelta(day=31) # End of last month
        
        # However, requirements say "Day of month". If I set day=10, do I want Prev Month or Current Month up to 10th?
        # Let's assume standard practice: Full month statement for PREVIOUS month, sent on X day of CURRENT month.
        
        wizard = self.env['partner.statement.wizard'].create({
            'company_id': self.id,
            'partner_ids': [(6, 0, partners_to_send.ids)],
            'date_from': date_from,
            'date_to': date_to_report,
            'target_move': 'posted',
            'account_type': 'receivable' if self.soa_statement_type == 'customer' else 'payable' if self.soa_statement_type == 'vendor' else 'both',
            'show_aging': True,
            'show_running_balance': True,
        })
        
        # Trigger email sending
        wizard.action_send_email()
