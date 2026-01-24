
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print("AUDITING VENDOR BILL STATUSES")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    # States to check
    states = ['not_paid', 'in_payment', 'paid', 'partial', 'reversed']
    
    for s in states:
        ids = models.execute_kw(DB, uid, PASS, 'account.move', 'search', [[('move_type', '=', 'in_invoice'), ('payment_state', '=', s)]])
        print(f"State '{s}': {len(ids)} Bills")
        if ids:
            # Check how many have 0 residual
            zero_res = models.execute_kw(DB, uid, PASS, 'account.move', 'search_count', [[('id', 'in', ids), ('amount_residual', '=', 0)]])
            print(f"  -> {zero_res} have 0 residual")
            
    # Also check total bills
    total = models.execute_kw(DB, uid, PASS, 'account.move', 'search_count', [[('move_type', '=', 'in_invoice')]])
    print(f"\nTotal Vendor Bills: {total}")

if __name__ == "__main__":
    main()
