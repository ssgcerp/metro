
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def fix_mysore_taxes_draft_post(env):
    """
    Fixes tax lines for Mysore Restaurant invoices by:
    1. Resetting to Draft
    2. Changing Account from Sales (500001) to VAT Output (201017)
    3. Posting again
    """
    print("\n--- Starting Mysore Tax Fix (Draft -> Fix -> Post) ---")
    
    # 1. Identify Company
    company_domain = [('name', 'ilike', 'Mysore')]
    companies = env['res.company'].search(company_domain)
    
    if not companies:
        print("Error: Company 'Mysore' not found.")
        return

    for company in companies:
        print(f"Processing Company: {company.name} (ID: {company.id})")
        
        # 2. Find Accounts
        sales_account = env['account.account'].search([
            ('company_id', '=', company.id),
            ('code', '=', '500001')
        ], limit=1)
        
        vat_account = env['account.account'].search([
            ('company_id', '=', company.id),
            # ('name', 'ilike', 'VAT Output'), # Using code is safer if name varies
            ('code', '=', '201017')
        ], limit=1)

        if not sales_account or not vat_account:
            print(f"  Error: Accounts not found. Sales: {sales_account}, VAT: {vat_account}")
            continue
            
        print(f"  Sales Account: {sales_account.code}")
        print(f"  Target VAT Account: {vat_account.code}")
        
        # 3. Find Incorrect Invoices
        # Find moves that have at least one line with tax_line_id set AND account_id = sales_account
        incorrect_moves = env['account.move'].search([
            ('company_id', '=', company.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('line_ids', 'any', [
                ('tax_line_id', '!=', False),
                ('account_id', '=', sales_account.id)
            ])
        ])
        
        print(f"  Found {len(incorrect_moves)} invoices to fix.")
        
        if not incorrect_moves:
            print("  No incorrect invoices found.")
            continue

        # 4. Process Fix
        success_count = 0
        error_count = 0
        
        for move in incorrect_moves:
            print(f"    Processing Invoice {move.name} (ID: {move.id})...")
            try:
                # A. Reset to Draft
                move.button_draft()
                
                # B. Update Lines
                # We need to find the specific lines again because we are iterating over moves
                lines_to_fix = move.line_ids.filtered(
                    lambda l: l.tax_line_id and l.account_id.id == sales_account.id
                )
                
                if not lines_to_fix:
                    print("      No lines found to fix after drafting (unexpected).")
                    continue
                    
                for line in lines_to_fix:
                    print(f"      Updating line {line.id} - Credit: {line.credit}")
                    line.write({'account_id': vat_account.id})
                
                # C. Post Again
                move.action_post()
                print("      Successfully Re-posted.")
                success_count += 1
                
                # Commit every few records if needed, or just let the script finish
                # env.cr.commit() 
                
            except Exception as e:
                print(f"      FAILED: {e}")
                error_count += 1
                # Rollback specific transaction logic isn't easily available here without savepoints, 
                # but Odoo shell usually runs in one transaction unless committed. 
                # If an exception occurs, we should log it. 
                # Ideally, we should skip this move and continue, but in Odoo shell exceptions might break the loop.
                # using a savepoint is recommended.
                # with env.cr.savepoint(): # Only works if supported by environment context wrapper
                pass

    print(f"\n--- Fix Complete ---")
    print(f"Success: {success_count}")
    print(f"Errors: {error_count}")
    
    env.cr.commit()

if __name__ == '__main__':
    try:
        fix_mysore_taxes_draft_post(env)
    except NameError:
        print("Run within Odoo Shell.")
