import xmlrpc.client
import ssl

def main():
    url = "https://metro.equdaierp.com"
    db = "metrodb"
    username = "admin"
    password = "Amaze@321"

    print(f"Connecting to {url}...")
    
    context = ssl._create_unverified_context()
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=context)
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=context)
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("Authentication failed")
        return

    fields = models.execute_kw(db, uid, password, 'res.company', 'fields_get', [], {'attributes': ['string', 'type', 'name']})
    
    print("\nChecking res.company fields:")
    for f in ['code', 'abbreviation', 'branch_code']:
        if f in fields:
            print(f"YES: {f} exists")
        else:
            print(f"NO: {f} does not exist")

    # Also check values for company with id 1 (or user company)
    company = models.execute_kw(db, uid, password, 'res.company', 'search_read', [[('id', '=', 1)]], {'fields': ['name']})
    if company:
        print(f"Main Company: {company[0]['name']}")

if __name__ == "__main__":
    main()
