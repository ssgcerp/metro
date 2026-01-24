import xmlrpc.client
import ssl
import sys

# Odoo 19 Config
url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321" # Assuming same password

def main():
    print(f"Connecting to {url}...")
    try:
        # Create unverified context to avoid SSL errors with self-signed or internal certs if any
        context = ssl._create_unverified_context()
        
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=context)
        uid = common.authenticate(db, username, password, {})
        
        if not uid:
            print("Authentication Failed!")
            return

        print(f"Authenticated successfully (UID: {uid})")
        
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=context)
        
        # Check Fields of account.account
        fields_data = models.execute_kw(db, uid, password, 'account.account', 'fields_get', [], {'attributes': ['string', 'type', 'help']})
        
        print("\nChecking Fields:")
        if 'company_id' in fields_data:
            print(f"- company_id: {fields_data['company_id']}")
        else:
            print("- company_id: NOT FOUND")
            
        if 'company_ids' in fields_data:
            print(f"- company_ids: {fields_data['company_ids']}")
        else:
            print("- company_ids: NOT FOUND")

        if 'check_company_auto' in fields_data:
            print(f"- check_company_auto: {fields_data['check_company_auto']}")
            
        # Check if we can write company_id=False
        # We won't actually write, just want to know if field is required=True?
        # fields_get usually doesn't return 'required' unless requested.
        
        fields_attr = models.execute_kw(db, uid, password, 'account.account', 'fields_get', [['company_id'], ['required']])
        if 'company_id' in fields_attr:
             print(f"- company_id required: {fields_attr['company_id'].get('required', False)}")
             
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == '__main__':
    main()
