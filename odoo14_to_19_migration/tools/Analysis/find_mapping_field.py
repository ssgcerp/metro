import xmlrpc.client
import ssl

# Odoo 19 Config
url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321" 

def main():
    context = ssl._create_unverified_context()
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=context)
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("Auth Failed")
        return

    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=context)
    
    fields = models.execute_kw(db, uid, password, 'account.account', 'fields_get', [], {'attributes': ['relation', 'type']})
    
    target_model = 'account.code.mapping'
    
    found = False
    for fname, props in fields.items():
        if props.get('relation') == target_model:
            print(f"FOUND MATCH: Field '{fname}' -> {target_model}")
            found = True
            
    if not found:
        print(f"No field found on account.account pointing to {target_model}")

if __name__ == '__main__':
    main()
