import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metro"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def debug_fields():
    print("Fetching fields for account.account...")
    fields = models.execute_kw(db, uid, password, 'account.account', 'fields_get', [], {'attributes': ['string', 'type']})
    
    print("Fields containing 'company':")
    for field in fields:
        if 'company' in field:
            print(f" - {field}: {fields[field]['type']}")

if __name__ == "__main__":
    debug_fields()
