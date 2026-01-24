
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
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
    
    pid = 9393
    target_acc_id = 215 # ADCB Bank
    
    print(f"Testing Force Write on POSTED Payment {pid}...")
    
    # Ensure it is posted/in_process
    # It is currently in_process (from 1958)
    
    try:
        models.execute_kw(DB, uid, PASS, 'account.payment', 'write', [[pid], {'outstanding_account_id': target_acc_id}])
        print("Write executed on Posted Payment.")
    except Exception as e:
        print(f"Write FAILED: {e}")
        
    # Check
    data = models.execute_kw(DB, uid, PASS, 'account.payment', 'read', [[pid], ['state', 'outstanding_account_id']])[0]
    print(f"Result: {data}")
    
    # Also check if it became 'posted' (unlikely just by changing account, need to check if recompute triggers)
    
    # 4. Check
    data = models.execute_kw(DB, uid, PASS, 'account.payment', 'read', [[pid], ['state', 'outstanding_account_id']])[0]
    print(f"Result: {data}")

if __name__ == "__main__":
    main()
