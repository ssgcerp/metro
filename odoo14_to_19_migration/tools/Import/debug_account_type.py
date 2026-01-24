
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
    
    # Check IDs found in previous steps: 215, 1758, 232, 1205, etc.
    # Or just search for the ones used in 9394 (1758) and 9393 (215)
    acc_ids = [215, 1758]
    
    print(f"Checking Account Types for {acc_ids}...")
    accs = models.execute_kw(DB, uid, PASS, 'account.account', 'read', [acc_ids, ['name', 'account_type', 'code']])
    
    for a in accs:
        print(f"ID {a['id']} ({a['code']} {a['name']}): Type='{a['account_type']}'")
        
        if a['account_type'] != 'asset_cash':
             print(f"  -> WARNING: Should be 'asset_cash' (Bank and Cash)!")

if __name__ == "__main__":
    main()
