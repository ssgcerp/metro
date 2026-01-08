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
    
    # Get fields for res.groups.privilege
    try:
        fields = models.execute_kw(db, uid, password, 'res.groups.privilege', 'fields_get', [], {'attributes': ['string', 'type', 'name']})
        
        print("\nAll Fields in res.groups.privilege:")
        for field in sorted(fields.keys()):
            print(f" - {field}: {fields[field]['string']} ({fields[field]['type']})")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
