import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
src_db = 'metrodb'
username = 'admin'
password = 'Amaze@321'
company_name = 'DUBAI'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context(), allow_none=True)
src_uid = common.authenticate(src_db, username, password, {})
src_models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context(), allow_none=True)

src_company_id = src_models.execute_kw(src_db, src_uid, password, 'res.company', 'search', [[('name', '=', company_name)]])[0]

# Get ALL payments for DUBAI company regardless of state or type
all_pays = src_models.execute_kw(src_db, src_uid, password, 'account.payment', 'search_read', 
    [[('company_id', '=', src_company_id)]], 
    {'fields': ['name', 'state', 'payment_type', 'partner_type']}
)

print(f"Total payments in DUBAI: {len(all_pays)}")

breakdown = {}
for p in all_pays:
    key = f"{p['payment_type']} | {p['partner_type']} | {p['state']}"
    breakdown[key] = breakdown.get(key, 0) + 1

for k, v in sorted(breakdown.items()):
    print(f"  {k}: {v}")
