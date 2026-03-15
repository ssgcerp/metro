import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

ctx = ssl._create_unverified_context()
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ctx, allow_none=True)
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ctx, allow_none=True)

# Find all posted vendor bills
domain = [('move_type', '=', 'in_invoice'), ('state', '=', 'posted')]
bill_ids = models.execute_kw(db, uid, password, 'account.move', 'search', [domain])
print(f"Found {len(bill_ids)} posted vendor bills.")

if not bill_ids:
    print("No bills to draft.")
    exit()

# Batch process
batch_size = 50
success = 0
errors = 0

for i in range(0, len(bill_ids), batch_size):
    batch = bill_ids[i:i + batch_size]
    print(f"Processing batch {i//batch_size + 1} ({len(batch)} bills)...")
    try:
        try:
            models.execute_kw(db, uid, password, 'account.move', 'button_draft', [batch])
        except Exception as e:
            if 'marshal None' not in str(e):
                raise
        success += len(batch)
        print(f"  Drafted {len(batch)} bills.")
    except Exception as e:
        print(f"  Error on batch: {e}")
        errors += len(batch)

print(f"\n--- Summary ---")
print(f"Total found: {len(bill_ids)}")
print(f"Successfully drafted: {success}")
print(f"Errors: {errors}")
