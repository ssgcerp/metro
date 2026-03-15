import xmlrpc.client
import ssl

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

context = ssl._create_unverified_context()
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=context)
uid = common.authenticate(db, username, password, {})

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=context)

configs = models.execute_kw(db, uid, password, 'odoo14.migration.config', 'search_read', [[]], {'fields': ['display_name', 'odoo14_url', 'odoo14_database']})

print("Existing Migration Configurations:")
for c in configs:
    print(f"ID: {c['id']}, Name: {c['display_name']}, URL: {c['odoo14_url']}, DB: {c['odoo14_database']}")
