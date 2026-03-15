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

# Find all posted customer invoices
domain = [('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]
invoice_ids = models.execute_kw(db, uid, password, 'account.move', 'search', [domain])
print(f"Found {len(invoice_ids)} posted customer invoices.")

if not invoice_ids:
    print("No invoices to draft.")
    exit()

# Batch process
batch_size = 50
success = 0
errors = 0

for i in range(0, len(invoice_ids), batch_size):
    batch = invoice_ids[i:i + batch_size]
    print(f"Processing batch {i//batch_size + 1} ({len(batch)} invoices)...")
    try:
        try:
            models.execute_kw(db, uid, password, 'account.move', 'button_draft', [batch])
        except Exception as e:
            if 'marshal None' not in str(e):
                raise
        success += len(batch)
        print(f"  Drafted {len(batch)} invoices.")
    except Exception as e:
        print(f"  Error on batch: {e}")
        errors += len(batch)

print(f"\n--- Summary ---")
print(f"Total found: {len(invoice_ids)}")
print(f"Successfully drafted: {success}")
print(f"Errors: {errors}")
