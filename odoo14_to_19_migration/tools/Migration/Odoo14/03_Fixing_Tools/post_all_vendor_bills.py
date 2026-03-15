import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context(), allow_none=True)
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context(), allow_none=True)

# Find all draft vendor bills (in_invoice)
domain = [
    ('move_type', '=', 'in_invoice'),
    ('state', '=', 'draft')
]

bills = models.execute_kw(db, uid, password, 'account.move', 'search_read', [domain], {'fields': ['id', 'name', 'ref']})

print(f"Found {len(bills)} draft vendor bills to post in newdb.")

posted = 0
failed = 0

for b in bills:
    bill_id = b['id']
    bill_name = b['name'] if b['name'] != '/' else f"Draft Bill ({b['ref'] or bill_id})"
    
    try:
        print(f"Posting bill: {bill_name} (ID: {bill_id})...", end=' ')
        models.execute_kw(db, uid, password, 'account.move', 'action_post', [[bill_id]])
        posted += 1
        print("Success")
        
    except Exception as e:
        print(f"Failed: {e}")
        failed += 1

print("\n--- Summary ---")
print(f"Total found: {len(bills)}")
print(f"Successfully posted: {posted}")
print(f"Failed to post: {failed}")
