import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'metrodb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

# Get ABU DHABI company ID
comp = models.execute_kw(db, uid, password, 'res.company', 'search', [[('name', '=', 'ABU DHABI')]])
if comp:
    c_id = comp[0]
    print(f"Company ID for ABU DHABI: {c_id}")
    
    # Check payments
    domain = [
        ('payment_type', '=', 'inbound'),
        ('partner_type', '=', 'customer'),
        ('state', '=', 'posted'),
        ('company_id', '=', c_id)
    ]
    payments = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [domain], {'fields': ['name'], 'limit': 5})
    print(f"Found {len(payments)} payments with strict domain.")
    if not payments:
        # Try without state
        domain2 = [
            ('payment_type', '=', 'inbound'),
            ('partner_type', '=', 'customer'),
            ('company_id', '=', c_id)
        ]
        p2 = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [domain2], {'fields': ['name', 'state'], 'limit': 5})
        print(f"Without state: Found {len(p2)} payments. States: {[p['state'] for p in p2]}")
else:
    print("Company not found")
