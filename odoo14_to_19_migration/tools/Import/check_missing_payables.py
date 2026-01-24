
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
    
    print("Checking for 'in_process' payments with NO Destination (Payable) Account...")
    domain = [('state', '=', 'in_process'), ('partner_type', '=', 'supplier'), ('destination_account_id', '=', False)]
    ids = models.execute_kw(DB, uid, PASS, 'account.payment', 'search', [domain])
    
    print(f"Count with Missing Payable: {len(ids)}")
    if ids:
        print(f"Sample IDs: {ids[:5]}")
        pid = ids[0]
        data = models.execute_kw(DB, uid, PASS, 'account.payment', 'read', [[pid], ['partner_id']])
        print(f"Details of {pid}: {data}")

if __name__ == "__main__":
    main()
