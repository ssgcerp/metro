import xmlrpc.client
import ssl
import sys

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

context = ssl._create_unverified_context()
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=context)
uid = common.authenticate(db, username, password, {})

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=context)

# Inspect vendor.bill.migration.line fields
fields = models.execute_kw(db, uid, password, 'vendor.bill.migration.line', 'fields_get', [], {'attributes': ['string', 'type', 'relation']})

print("Fields for vendor.bill.migration.line:")
for field, attrs in fields.items():
    if field == 'config_id':
        print(f"Name: {field}, Type: {attrs['type']}, Relation: {attrs.get('relation')}")

