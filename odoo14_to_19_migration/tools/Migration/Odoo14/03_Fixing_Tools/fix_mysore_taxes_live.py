
import xmlrpc.client
import ssl
import sys

# Configuration from previous context
URL = "https://metro.equdaierp.com"
DB = "metrodb"
USERNAME = "admin"
PASSWORD = "Amaze@321" # From get_odoo14_credentials.py

def fix_mysore_taxes_live():
    print(f"Connecting to {URL} (DB: {DB})...")
    
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, USERNAME, PASSWORD, {})
        
        if not uid:
            print("Authentication Failed!")
            return

        print(f"Authenticated as User ID: {uid}")
        
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
        
        # 1. Identify Company
        print("Searching for Company 'Mysore'...")
        company_ids = models.execute_kw(DB, uid, PASSWORD, 
            'res.company', 'search', [[('name', 'ilike', 'Mysore')]], {'limit': 1})
            
        if not company_ids:
            print("Company 'Mysore' not found.")
            return

        company_id = company_ids[0]
        # Get Company Name for display
        company_name = models.execute_kw(DB, uid, PASSWORD,
            'res.company', 'read', [[company_id]], {'fields': ['name']})[0]['name']
        print(f"Processing Company: {company_name} (ID: {company_id})")

        # 2. Find Invoices
        print("Searching for ALL Posted Customer Invoices...")
        
        invoice_ids = models.execute_kw(DB, uid, PASSWORD, 'account.move', 'search', [[
                ('company_id', '=', company_id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted')
        ]])

        if not invoice_ids:
            print("No posted invoices found.")
            return

        print(f"Found {len(invoice_ids)} posted invoices.")

        # 3. Process Loop
        count = 1
        for move_id in invoice_ids:
            print(f"[{count}/{len(invoice_ids)}] Resetting Invoice ID {move_id} to Draft...")
            
            try:
                # A. Reset to Draft
                models.execute_kw(DB, uid, PASSWORD, 'account.move', 'button_draft', [[move_id]])
                print("  - Done.")
                
            except Exception as e:
                print(f"  - FAILED: {e}")
            
            count += 1
            
        print("\n--- Live Reset Complete ---")

    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    fix_mysore_taxes_live()
