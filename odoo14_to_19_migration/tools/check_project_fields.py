import argparse
import xmlrpc.client
import ssl

def main():
    url = "https://metro.equdaierp.com"
    db = "metrodb"
    username = "admin"
    password = "Amaze@321"

    print(f"Connecting to {url}...")
    
    # Ignore SSL context for some servers
    context = ssl._create_unverified_context()
    
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=context)
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("Authentication failed")
        return

    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=context)
    
    # Get fields for project.project
    fields = models.execute_kw(db, uid, password, 'project.project', 'fields_get', [], {'attributes': ['string', 'type', 'name']})
    
    print("\nPossible Project Code Fields:")
    for field, data in fields.items():
        if 'code' in field.lower() or 'code' in data['string'].lower():
            print(f" - {field}: {data['string']} ({data['type']})")

if __name__ == "__main__":
    main()
