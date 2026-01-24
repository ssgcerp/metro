
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print("Connecting...")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    print("Fetching 'account.journal' fields...")
    fields = models.execute_kw(DB, uid, PASS, 'account.journal', 'fields_get', [], {'attributes': ['string', 'type', 'name']})
    
    print("Fields containing 'account' or 'suspense':")
    for fname, fdef in fields.items():
        if 'account' in fname or 'suspense' in fname:
            print(f" - {fname} ({fdef['type']}): {fdef['string']}")

if __name__ == "__main__":
    main()
