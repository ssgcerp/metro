
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def fix_mysore_invoices_v2(env):
    """
    Fixes tax lines for Mysore Restaurant invoices.
    Logic:
    1. Find all Invoices for Mysore.
    2. Check if they have lines with Tax linked to Sales Account (500001).
    3. Reset to Draft -> Update Account -> Post.
    """
    print("\n--- Starting Mysore Invoice Fix (V2) ---")
    
    # 1. Identify Company
    company_domain = [('name', 'ilike', 'Mysore')]
    company = env['res.company'].search(company_domain, limit=1)
    
    if not company:
        print("Error: Company 'Mysore' not found.")
        return

    print(f"Processing Company: {company.name} (ID: {company.id})")
    
    # 2. Find correct accounts (Robust Search)
    # Search all accounts with code 500001 and 201017, then filter by company
    all_sales_accounts = env['account.account'].search([('code', '=', '500001')])
    all_vat_accounts = env['account.account'].search([('code', '=', '201017')])
    
    # Filter by company_ids (Odoo 19 shared accounts)
    # Check if account has no company (shared) or includes this company
    sales_account = all_sales_accounts.filtered(lambda a: not a.company_ids or company in a.company_ids)
    vat_account = all_vat_accounts.filtered(lambda a: not a.company_ids or company in a.company_ids)
    
    if not sales_account:
        print("  Error: Sales Account 500001 not found for this company.")
        
    if not vat_account:
        print("  Error: VAT Account 201017 not found for this company.")

    if not sales_account or not vat_account:
        print("  Aborting: Missing accounts.")
        return

    # Ensure singleton
    sales_account = sales_account[0]
    vat_account = vat_account[0]

    print(f"  Sales Account: {sales_account.code} (ID: {sales_account.id})")
    print(f"  Target VAT Account: {vat_account.code} (ID: {vat_account.id})")
    
    # 3. Find Invoices
    # Only search by company_id on account.move (standard field)
    # Filter for Posted Out Invoices
    invoices = env['account.move'].search([
        ('company_id', '=', company.id),
        ('move_type', '=', 'out_invoice'),
        ('state', '=', 'posted')
    ])
    
    print(f"  Found {len(invoices)} posted invoices. Checking for incorrect tax lines...")
    
    count_fixed = 0
    
    for invoice in invoices:
        # Check lines in Python to avoid complex domain issues
        incorrect_lines = invoice.line_ids.filtered(
            lambda l: l.tax_line_id and l.account_id == sales_account
        )
        
        if not incorrect_lines:
            continue
            
        print(f"    Fixing Invoice {invoice.name} (ID: {invoice.id}) - {len(incorrect_lines)} incorrect lines")
        
        try:
            # A. Reset to Draft
            print("      Resetting to Draft...")
            invoice.button_draft()
            
            # B. Fix Lines
            # Re-fetch lines as IDs persist
            for line in incorrect_lines:
                print(f"      Updating Line {line.id} (Account {line.account_id.code} -> {vat_account.code})")
                line.write({'account_id': vat_account.id})
                
            # C. Post
            print("      Posting...")
            invoice.action_post()
            print("      Done.")
            count_fixed += 1
            
            # Commit processing of this invoice
            # env.cr.commit()
            
        except Exception as e:
            print(f"      ERROR: {e}")
            
    print(f"\n--- Process Complete. Fixed {count_fixed} invoices. ---")
    env.cr.commit()

if __name__ == '__main__':
    try:
        fix_mysore_invoices_v2(env)
    except NameError:
        print("Run within Odoo Shell.")
