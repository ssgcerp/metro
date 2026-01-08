import xmlrpc.client
import ssl

def main():
    url = "https://metro.equdaierp.com"
    db = "metrodb"
    username = "admin"
    password = "Amaze@321"

    print(f"Connecting to {url}...")
    
    context = ssl._create_unverified_context()
    
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=context)
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("Authentication failed")
        return

    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=context)
    
    # Get fields for res.groups
    fields = models.execute_kw(db, uid, password, 'res.groups', 'fields_get', [], {'attributes': ['string', 'type', 'name']})
    
    print("\nPossible Category Fields in res.groups:")
    found = False
    for field, data in fields.items():
        if 'cat' in field.lower():
            print(f" - {field}: {data['string']} ({data['type']})")
            found = True
            
    print("\nAll Fields in res.groups:")
    for field in sorted(fields.keys()):
        print(f" - {field}")

if __name__ == "__main__":
    main()
