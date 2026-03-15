import xmlrpc.client
import ssl

url = 'https://erpmfs.com'
db = 'metro_production_8_8_22'
user = 'Sales.auh@metrofiresystems.com'
pwd = 'Sales@185734'
ctx = ssl._create_unverified_context()

common = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/common', context=ctx, allow_none=True)
uid = common.authenticate(db, user, pwd, {})

models = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/object', context=ctx, allow_none=True)

# Query Odoo 14 account.move fields
print("Fetching fields for account.move from Odoo 14...")
fields = models.execute_kw(db, uid, pwd, 'account.move', 'fields_get', [], {'attributes': ['string', 'type']})

for f in ['type', 'discount_type', 'discount_rate', 'amount_discount']:
    if f in fields:
        print(f"✅ {f}: YES (Type: {fields[f]['type']})")
    else:
        print(f"❌ {f}: NO")
