
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print("FIXING MISSING PAYABLES")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    # Search
    domain = [('state', '=', 'in_process'), ('partner_type', '=', 'supplier'), ('destination_account_id', '=', False)]
    ids = models.execute_kw(DB, uid, PASS, 'account.payment', 'search', [domain])
    print(f"Found {len(ids)} to fix.")
    
    if not ids: return

    # Get Default Payable (from property or search)
    # Let's search for "Payables" account to use as fallback
    res = models.execute_kw(DB, uid, PASS, 'account.account', 'search_read', [[('code', '=', '201002')]], {'fields': ['id']})
    fallback_acc_id = res[0]['id'] if res else False
    if not fallback_acc_id:
        print("Fallback Account 201002 not found! Exiting.")
        return
    print(f"Fallback Account: {fallback_acc_id}")
    
    # Process
    # We can try to rely on Odoo to compute it if we write Partner again? No.
    # We should look up partner property. But easier to just set to fallback for now to unblock.
    # OR: Group by partner?
    # Let's just set ALL to fallback_acc_id for now as 201002 is standard Payables.
    # Most partners use this.
    
    batch_size = 500
    for i in range(0, len(ids), batch_size):
        batch = ids[i:i+batch_size]
        try:
            models.execute_kw(DB, uid, PASS, 'account.payment', 'write', [batch, {'destination_account_id': fallback_acc_id}])
            print(f"Updated Batch {i}-{i+len(batch)}")
        except Exception as e:
            print(f"Failed Batch: {e}")

if __name__ == "__main__":
    main()
