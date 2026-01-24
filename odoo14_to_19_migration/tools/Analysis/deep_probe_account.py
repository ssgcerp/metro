import xmlrpc.client
import ssl
import sys

# Odoo 19 Config
url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321" 

def main():
    print(f"Connecting to {url}...")
    context = ssl._create_unverified_context()
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=context)
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("Authentication Failed!")
        return

    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=context)
    
    # Get all fields
    fields_data = models.execute_kw(db, uid, password, 'account.account', 'fields_get', [], {'attributes': ['string', 'type', 'relation', 'help']})
    
    print("\n--- Analysing Fields ---")
    
    # Check One2many fields to identifier the "Mapping" tab
    o2m_fields = {k: v for k, v in fields_data.items() if v['type'] == 'one2many'}
    
    print(f"\nFound {len(o2m_fields)} One2many fields:")
    for k, v in o2m_fields.items():
        print(f"[{k}] Type: {v['type']}, Relation: {v.get('relation')}, String: {v.get('string')}")
        
    print("\n--- Inspecting Specific Relations ---")
    # If we find something like 'account.account.mapping' or 'code', inspect it.
    
    potential_matches = []
    
    for k, v in o2m_fields.items():
        rel = v.get('relation', '')
        if 'code' in k or 'map' in k or 'company' in k:
            potential_matches.append((k, rel))
            
    if not potential_matches:
        print("No obvious mapping fields found by name. Dumping all o2m relations might be needed.")
    else:
        for fname, relation in potential_matches:
             print(f"\nINSPECTING Relation: {relation} (Field: {fname})")
             # Check fields of this related model
             try:
                 rel_fields = models.execute_kw(db, uid, password, relation, 'fields_get', [], {'attributes': ['string', 'type', 'name']})
                 print(f"  Fields in {relation}: {list(rel_fields.keys())}")
             except Exception as e:
                 print(f"  Could not inspect {relation}: {e}")

if __name__ == '__main__':
    main()
