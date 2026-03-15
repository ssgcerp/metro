import xmlrpc.client
import ssl
import pandas as pd

# Connection details
url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'
excel_path = r"e:\odoo modules\19\metro\odoo14_to_19_migration\tools\Docs\Payments (account.payment) (1).xlsx"

# 1. Read Excel list
df_excel = pd.read_excel(excel_path)
correct_names = set(df_excel['Number'].astype(str).unique())
print(f"Correct names in Excel: {len(correct_names)}")

# 2. Connect to Odoo
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context(), allow_none=True)
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context(), allow_none=True)

# 3. Get all DUBAI customer inbound payments
domain = [
    ('company_id.name', '=', 'DUBAI'),
    ('partner_type', '=', 'customer'),
    ('payment_type', '=', 'inbound')
]
pays = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [domain], {'fields': ['id', 'name']})
print(f"Total payments in NewDB for DUBAI: {len(pays)}")

# 4. Identify extras
to_delete = []
for p in pays:
    if p['name'] not in correct_names:
        to_delete.append(p)

print(f"Found {len(to_delete)} extra payments to delete.")

# 5. Delete extras
deleted_count = 0
for p in to_delete:
    print(f"Deleting extra payment: {p['name']} (ID: {p['id']})")
    try:
        # Force cancel/draft if needed
        try: models.execute_kw(db, uid, password, 'account.payment', 'action_draft', [[p['id']]])
        except: pass
        try: models.execute_kw(db, uid, password, 'account.payment', 'action_cancel', [[p['id']]])
        except: pass
        
        models.execute_kw(db, uid, password, 'account.payment', 'unlink', [[p['id']]])
        deleted_count += 1
    except Exception as e:
        print(f"  FAILED to delete {p['name']}: {e}")

print(f"\nSuccessfully deleted {deleted_count} extra payments.")

# 6. Final check
final_count = models.execute_kw(db, uid, password, 'account.payment', 'search_count', [domain])
print(f"Final payment count for DUBAI in NewDB: {final_count}")
