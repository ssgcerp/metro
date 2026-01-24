
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print("AUDITING UNRECONCILED PAYMENTS")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    # Search for supplier payments that are posted/paid and NOT reconciled
    # In Odoo 19, account.payment doesn't have a direct 'is_reconciled' field usually (it's often a compute or on the move line).
    # But let's check the account.move.line instead.
    
    # 1. Get all supplier payments
    print("Fetching payments...")
    p_ids = models.execute_kw(DB, uid, PASS, 'account.payment', 'search', [[('partner_type', '=', 'supplier'), ('state', 'in', ['posted', 'paid'])]])
    print(f"Total Supplier Payments: {len(p_ids)}")
    
    # 2. Check their move lines
    # Fetch moves
    p_data = models.execute_kw(DB, uid, PASS, 'account.payment', 'read', [p_ids, ['move_id']])
    mids = [p['move_id'][0] for p in p_data if p['move_id']]
    
    # Search lines on these moves with payable account
    print("Checking move lines...")
    l_ids = models.execute_kw(DB, uid, PASS, 'account.move.line', 'search', [[('move_id', 'in', mids), ('account_id.account_type', '=', 'liability_payable')]])
    
    # Check full_reconcile_id
    reconciled_count = models.execute_kw(DB, uid, PASS, 'account.move.line', 'search_count', [[('id', 'in', l_ids), ('full_reconcile_id', '!=', False)]])
    unreconciled_count = models.execute_kw(DB, uid, PASS, 'account.move.line', 'search_count', [[('id', 'in', l_ids), ('full_reconcile_id', '=', False)]])
    
    print(f"Reconciled Payments: {reconciled_count}")
    print(f"Unreconciled Payments: {unreconciled_count}")

if __name__ == "__main__":
    main()
