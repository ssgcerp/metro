import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'metrodb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

# Search payments directly
payments = models.execute_kw(db, uid, password, 'account.payment', 'search_read', 
    [[('payment_type', '=', 'inbound')]], 
    {'fields': ['journal_id', 'company_id', 'state']})

used_journals = {}
for p in payments:
    if p.get('company_id') and p.get('journal_id') and p.get('state') == 'posted':
        c_name = p['company_id'][1]
        j_name = p['journal_id'][1]
        
        if c_name not in used_journals:
            used_journals[c_name] = set()
        used_journals[c_name].add(j_name)
    
for c, j_set in used_journals.items():
    print(f"\nCompany: {c} used these journals for payments:")
    for j in j_set:
        print(f"  - {j}")
