
import xmlrpc.client
import sys
import time

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print("="*80)
    print("VALIDATE (REFRESH STATE) FOR ALL IN PROCESS PAYMENTS")
    print("="*80)
    
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
    
    # 1. Search ALL In Process
    domain = [('state', '=', 'in_process'), ('partner_type', '=', 'supplier')]
    ids = models.execute_kw(DB, uid, PASS, 'account.payment', 'search', [domain])
    print(f"Found {len(ids)} payments to validate.")
    
    if not ids:
        print("Done.")
        return

    # 2. Process in Batches
    batch_size = 500
    for i in range(0, len(ids), batch_size):
        batch = ids[i:i+batch_size]
        print(f"Processing Batch {i}-{i+len(batch)}...")
        try:
            # Calling action_post on already posted payments acts as a refresh/check
            models.execute_kw(DB, uid, PASS, 'account.payment', 'action_post', [batch])
            print(f"  -> Batch Validated.")
        except Exception as e:
            print(f"  -> FAILED batch (likely XMLRPC None Error which is OK): {e}")

    # 3. Final Verification
    print("\nFinal Verification Count:")
    rem_ids = models.execute_kw(DB, uid, PASS, 'account.payment', 'search', [domain])
    print(f"Remaining In Process: {len(rem_ids)}")

if __name__ == "__main__":
    main()
