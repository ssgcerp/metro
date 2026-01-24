
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print("Connecting...")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    print("Searching for 'in_process' Supplier Payments...")
    domain = [('state', '=', 'in_process'), ('partner_type', '=', 'supplier')]
    ids = models.execute_kw(DB, uid, PASS, 'account.payment', 'search', [domain])
    
    print(f"Count: {len(ids)}")
    if ids:
        print(f"Sample IDs: {ids[:5]}")
        # Inspect one
        pid = ids[0]
        data = models.execute_kw(DB, uid, PASS, 'account.payment', 'read', [[pid], ['name', 'outstanding_account_id', 'is_reconciled']])
        print(f"Details of {pid}: {data}")

if __name__ == "__main__":
    main()
