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

# Load Excel - get the bill numbers to KEEP
df = pd.read_excel(r'e:\odoo modules\19\metro\odoo14_to_19_migration\tools\Reset\correct_vendor_bills.xlsx')
keep_numbers = set(str(n).strip() for n in df['Number'].dropna().tolist())
print(f"Bills to KEEP (from Excel): {len(keep_numbers)}")

# Fetch all vendor bills from Odoo 19
print("Fetching all vendor bills from Odoo 19...")
domain = [('move_type', 'in', ['in_invoice', 'in_receipt'])]

batch_size = 500
offset = 0
all_bills = []  # list of (id, name, state)

while True:
    results = models.execute_kw(db, uid, password, 'account.move', 'search_read', [domain],
                                {'fields': ['name', 'state'], 'limit': batch_size, 'offset': offset})
    if not results:
        break
    all_bills.extend(results)
    offset += batch_size
    print(f"  Fetched {offset} so far...")

print(f"Total vendor bills in Odoo 19: {len(all_bills)}")

# Identify bills to DELETE (not in Excel)
to_delete = [
    (b['id'], b['name'], b['state']) for b in all_bills
    if isinstance(b['name'], str) and b['name'].strip() not in keep_numbers
]
print(f"Bills to DELETE (not in Excel): {len(to_delete)}")

if not to_delete:
    print("Nothing to delete.")
    exit()

# Process deletions in batches
deleted = 0
errors = 0
batch_size_del = 50

delete_ids = [b[0] for b in to_delete]

for i in range(0, len(delete_ids), batch_size_del):
    batch = delete_ids[i:i + batch_size_del]
    batch_num = i // batch_size_del + 1
    print(f"Deleting batch {batch_num} ({len(batch)} bills)...")
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
        print(f"  Deleted {len(batch)} bills.")
    except Exception as e:
        print(f"  Error on batch {batch_num}: {e}")
        errors += len(batch)

print(f"\n--- Summary ---")
print(f"Total to delete: {len(to_delete)}")
print(f"Successfully deleted: {deleted}")
print(f"Errors: {errors}")
