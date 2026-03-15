import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context(), allow_none=True)
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context(), allow_none=True)

# Find all inbound customer payments
domain = [
    ('payment_type', '=', 'inbound'),
    ('partner_type', '=', 'customer')
]

pay_ids = models.execute_kw(db, uid, password, 'account.payment', 'search', [domain])
print(f"Found {len(pay_ids)} customer inbound payments to delete in newdb.")

if not pay_ids:
    print("No payments to delete.")
    exit()

# Batch process in chunks of 100 for safety
batch_size = 100
for i in range(0, len(pay_ids), batch_size):
    batch = pay_ids[i:i + batch_size]
    print(f"Processing batch {i//batch_size + 1} ({len(batch)} payments)...")
    
    # Force to draft and cancel
    try:
        models.execute_kw(db, uid, password, 'account.payment', 'action_draft', [batch])
    except Exception as e:
        print(f"  Warning during draft: {e}")
        
    try:
        models.execute_kw(db, uid, password, 'account.payment', 'action_cancel', [batch])
    except Exception as e:
        print(f"  Warning during cancel: {e}")
        
    # Delete
    try:
        models.execute_kw(db, uid, password, 'account.payment', 'unlink', [batch])
        print(f"  Deleted batch of {len(batch)} payments.")
    except Exception as e:
        print(f"  Failed to delete batch: {e}")

print("\n--- Summary ---")
print(f"Total processed: {len(pay_ids)}")
