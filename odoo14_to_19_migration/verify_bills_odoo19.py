
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print(f"Connecting to {URL}...")
    try:
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL))
        uid = common.authenticate(DB, USER, PASS, {})
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL))
        
        # Load bills to check
        with open("e:\\odoo modules\\19\\metro\\odoo14_to_19_migration\\bills_to_verify.txt", "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
            
        print(f"Checking {len(lines)} bills...")
        
        # Fetch all bills from Odoo 19 to check against
        # We fetch fields that might contain the reference
        print("Fetching existing bills from Odoo 19...")
        server_bills = models.execute_kw(DB, uid, PASS, 'account.move', 'search_read', 
            [[('move_type', '=', 'in_invoice')]], 
            {'fields': ['name', 'ref', 'payment_reference']})
            
        # Create lookup sets
        existing_refs = set()
        for b in server_bills:
            if b.get('name'): existing_refs.add(str(b['name']).strip())
            if b.get('ref'): existing_refs.add(str(b['ref']).strip())
            if b.get('payment_reference'): existing_refs.add(str(b['payment_reference']).strip())
            
        found = []
        missing = []
        
        for bill_ref in lines:
            if bill_ref in existing_refs:
                found.append(bill_ref)
            else:
                missing.append(bill_ref)
        
        print("\n" + "="*50)
        print("VERIFICATION REPORT")
        print("="*50)
        print(f"Total Checked: {len(lines)}")
        print(f"Found in Odoo 19: {len(found)}")
        print(f"Missing in Odoo 19: {len(missing)}")
        print("-" * 50)
        
        if missing:
            print("\nMISSING BILLS:")
            for m in missing:
                print(f" - {m}")
        else:
            print("\nALL BILLS FOUND!")
            
        print("="*50)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
