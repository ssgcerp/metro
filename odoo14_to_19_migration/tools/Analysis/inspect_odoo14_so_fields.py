import xmlrpc.client
import sys

url = 'https://erpmfs.com'
db = 'metro_production_8_8_22'
username = 'Sales.auh@metrofiresystems.com'
password = 'Sales@185734'

try:
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    if not uid:
        print("Auth failed for Odoo 14")
        sys.exit(1)
        
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    # Get all fields for sale.order
    so_fields = models.execute_kw(db, uid, password, 'sale.order', 'fields_get', [], {'attributes': ['type', 'relation', 'string']})
    print("--- Odoo 14 SALE ORDER FIELDS ---")
    branch_fields = {k: v for k, v in so_fields.items() if 'branch' in k or 'company' in k}
    for fname, fprops in branch_fields.items():
        print(f"{fname} ({fprops['type']}) -> {fprops.get('relation')} [{fprops.get('string')}]")

except Exception as e:
    print(f"Error: {e}")
