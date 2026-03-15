import xmlrpc.client
import ssl
import pandas as pd

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

ctx = ssl._create_unverified_context()
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ctx, allow_none=True)
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ctx, allow_none=True)

# Load Excel - get the invoice numbers to KEEP
df = pd.read_excel(r'e:\odoo modules\19\metro\odoo14_to_19_migration\tools\Reset\correct_customer_invoices.xlsx')
keep_numbers = set(str(n).strip() for n in df['Number'].dropna().tolist())
print(f"Customer Invoices to KEEP (from Excel): {len(keep_numbers)}")

# Fetch all customer invoices from Odoo 19
print("Fetching all customer invoices from Odoo 19...")
domain = [('move_type', 'in', ['out_invoice', 'out_receipt'])]

batch_size = 500
offset = 0
all_invoices = []  # list of (id, name, state)

while True:
    results = models.execute_kw(db, uid, password, 'account.move', 'search_read', [domain],
                                {'fields': ['name', 'state'], 'limit': batch_size, 'offset': offset})
    if not results:
        break
    all_invoices.extend(results)
    offset += batch_size
    print(f"  Fetched {offset} so far...")

print(f"Total customer invoices in Odoo 19: {len(all_invoices)}")

# Identify invoices to DELETE (not in Excel)
to_delete = [
    (inv['id'], inv['name'], inv['state']) for inv in all_invoices
    if isinstance(inv['name'], str) and inv['name'].strip() not in keep_numbers
]
print(f"Customer Invoices to DELETE (not in Excel): {len(to_delete)}")

if not to_delete:
    print("Nothing to delete.")
    exit()

# Process deletions in batches
deleted = 0
errors = 0
batch_size_del = 50

delete_ids = [inv[0] for inv in to_delete]

for i in range(0, len(delete_ids), batch_size_del):
    batch = delete_ids[i:i + batch_size_del]
    batch_num = i // batch_size_del + 1
    print(f"Deleting batch {batch_num} ({len(batch)} invoices)...")
    try:
        # Ensure draft first (some may still be posted)
        try:
            models.execute_kw(db, uid, password, 'account.move', 'button_draft', [batch])
        except Exception as e:
            if 'marshal None' not in str(e):
                print(f"  Warning on draft: {e}")

        # Delete
        models.execute_kw(db, uid, password, 'account.move', 'unlink', [batch])
        deleted += len(batch)
        print(f"  Deleted {len(batch)} invoices.")
    except Exception as e:
        print(f"  Error on batch {batch_num}: {e}")
        errors += len(batch)

print(f"\n--- Summary ---")
print(f"Total to delete: {len(to_delete)}")
print(f"Successfully deleted: {deleted}")
print(f"Errors: {errors}")
