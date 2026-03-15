import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context(), allow_none=True)
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context(), allow_none=True)

# Find customer payments that are in "in_process" state
domain = [
    ('payment_type', '=', 'inbound'),
    ('partner_type', '=', 'customer'),
    ('state', '=', 'in_process')
]

pay_ids = models.execute_kw(db, uid, password, 'account.payment', 'search', [domain])
print(f"Found {len(pay_ids)} customer payments in 'in_process' state.")

if not pay_ids:
    print("No payments to update.")
    exit()

# Batch process to avoid timeouts
batch_size = 100
for i in range(0, len(pay_ids), batch_size):
    batch = pay_ids[i:i + batch_size]
    print(f"Processing batch {i//batch_size + 1} ({len(batch)} payments)...")
    
    try:
        # Force the state to 'paid' directly
        models.execute_kw(db, uid, password, 'account.payment', 'write', [batch, {'state': 'paid'}])
        print(f"  Batch updated to 'paid'.")
    except Exception as e:
        print(f"  Attempt failed: {e}")

print("\n--- Summary ---")
print(f"Total processed: {len(pay_ids)}")
