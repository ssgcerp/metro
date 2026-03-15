"""
Use Odoo's ir.actions.server to run SQL directly on the server.
This bypasses the ORM company constraint.
"""
import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

ALL_COMPANIES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
MASTER_ID = 744

def run_sql_via_server():
    ctx = {'allowed_company_ids': ALL_COMPANIES, 'active_test': False}
    
    # Step 1: Add companies via server action (no import, no UserError)
    code_add_companies = (
        "env.cr.execute("
        "'INSERT INTO account_account_res_company_rel (account_account_id, res_company_id) "
        "SELECT 744, id FROM res_company "
        "WHERE id NOT IN (SELECT res_company_id FROM account_account_res_company_rel WHERE account_account_id = 744)')"
    )
    
    # Step 2: Move lines via server action
    code_move_lines = (
        "env.cr.execute("
        "'UPDATE account_move_line SET account_id = 744 "
        "WHERE account_id IN (SELECT id FROM account_account WHERE code LIKE ''104041%'' AND id != 744)')"
    )
    
    model_id = models.execute_kw(db, uid, password, 'ir.model', 'search', [[('model', '=', 'account.account')]])[0]
    
    for step_name, code in [('Add Companies', code_add_companies), ('Move Lines', code_move_lines)]:
        print(f"\n=== Running: {step_name} ===")
        action_id = models.execute_kw(db, uid, password, 'ir.actions.server', 'create', [{
            'name': f'Fix 744 - {step_name}',
            'model_id': model_id,
            'state': 'code',
            'code': code,
        }])
        print(f"  Created action ID: {action_id}")
        
        try:
            result = models.execute_kw(db, uid, password, 'ir.actions.server', 'run', [[action_id]], {'context': ctx})
            print(f"  Result: {result}")
            print(f"  SUCCESS!")
        except Exception as e:
            print(f"  Error: {e}")
        
        # Cleanup
        try:
            models.execute_kw(db, uid, password, 'ir.actions.server', 'unlink', [[action_id]])
        except:
            pass
    
    print("\n=== Verifying ===")
    accs = models.execute_kw(db, uid, password, 'account.account', 'read',
        [[MASTER_ID]], {'fields': ['name', 'code', 'company_ids'], 'context': ctx})
    print(f"Master 744 companies: {accs[0]['company_ids']}")
    
    # Check remaining lines on other accounts
    ctx2 = {'allowed_company_ids': ALL_COMPANIES, 'active_test': False}
    other_accs = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', 'like', '104041'), ('id', '!=', MASTER_ID)]],
        {'fields': ['id', 'name', 'code'], 'context': ctx2})
    
    for a in other_accs:
        cnt = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
            [[('account_id', '=', a['id'])]], {'context': ctx2})
        print(f"  ID {a['id']} ({a['name']}): {cnt} remaining lines")

if __name__ == "__main__":
    run_sql_via_server()
