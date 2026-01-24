import xmlrpc.client

# Potential Source Credentials (Localhost)
URL = "http://localhost:8079"
DB = "metrodb" # Guessing from other scripts
USER = "admin"
PASS = "Amaze@321"

def main():
    print(f"Connecting to {URL}...")
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        # Try finding DBs if authenticate fails?
        # print("DBs:", common.list()) # list() might not be available or requires admin pass
        
        uid = common.authenticate(DB, USER, PASS, {})
        if not uid:
             print("Auth failed or DB/User incorrect.")
             return

        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
        print(f"Connected as UID: {uid}")
        
        # Check purchase.order
        print("Inspecting purchase.order...")
        fields = models.execute_kw(DB, uid, PASS, 'purchase.order', 'fields_get', [], {'attributes': ['string', 'type', 'relation']})
        
        print("\nPossible Branch fields:")
        for field, props in fields.items():
            if 'branch' in field.lower() or 'branch' in props.get('string', '').lower():
                print(f"{field}: {props}")
        
        # Also check just 'branch_id' explicitly
        if 'branch_id' in fields:
            print("\nFound 'branch_id'!")
        else:
            print("\n'branch_id' not found in fields.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
