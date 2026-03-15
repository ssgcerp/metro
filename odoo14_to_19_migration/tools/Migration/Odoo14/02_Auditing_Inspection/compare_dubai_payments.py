import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
username = 'admin'
password = 'Amaze@321'
context = ssl._create_unverified_context()

def get_names(db, company_name):
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=context, allow_none=True)
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=context, allow_none=True)
    
    domain = [
        ('company_id.name', '=', company_name),
        ('partner_type', '=', 'customer'),
        ('payment_type', '=', 'inbound')
    ]
    pays = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [domain], {'fields': ['name', 'state', 'journal_id']})
    return {p['name']: (p['state'], p['journal_id'][1]) for p in pays}

src_data = get_names('metrodb', 'DUBAI')
dest_data = get_names('newdb', 'DUBAI')

src_names = set(src_data.keys())
dest_names = set(dest_data.keys())

extra = dest_names - src_names
missing = src_names - dest_names

print(f"Total in MetroDB: {len(src_names)}")
print(f"Total in NewDB: {len(dest_names)}")
print(f"\nExtra in NewDB ({len(extra)}):")
for name in sorted(list(extra))[:20]:
    print(f"  {name} - Journal: {dest_data[name][1]}")

print(f"\nMissing in NewDB ({len(missing)}):")
for name in sorted(list(missing))[:20]:
    print(f"  {name} - State: {src_data[name][0]}")
