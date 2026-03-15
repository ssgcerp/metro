
import xmlrpc.client
import logging
import csv
import os

# Credentials
URL_19 = "https://metro.equdaierp.com"
DB_19 = "metrodb"
USER_19 = "admin"
PASS_19 = "Amaze@321"

URL_14 = "https://erpmfs.com"
DB_14 = "metro_production_8_8_22"
USER_14 = "Sales.auh@metrofiresystems.com"
PASS_14 = "Sales@185734"

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def generate_missing_bills():
    try:
        # 1. Connect
        logger.info("Connecting to Odoo 19...")
        common_19 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_19))
        uid_19 = common_19.authenticate(DB_19, USER_19, PASS_19, {})
        models_19 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_19))
        
        logger.info("Connecting to Odoo 14...")
        common_14 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_14))
        uid_14 = common_14.authenticate(DB_14, USER_14, PASS_14, {})
        models_14 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_14))
        
        # 2. Fetch Odoo 19 Vendor Bills (Existing)
        logger.info("Fetching existing Odoo 19 Vendor Bills...")
        # move_type = 'in_invoice'
        existing_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'search_read', 
            [[('move_type', '=', 'in_invoice')]], {'fields': ['name', 'ref']})
        
        # Odoo 19 Name might differ if re-sequenced, but usually migration tries to keep name.
        # Also check 'ref' (Vendor Reference) as secondary match?
        # Ideally we match by Name if mapped correctly.
        names_19 = set()
        for r in existing_19:
            if r['name'] and r['name'] != '/':
                names_19.add(r['name'])
                
        logger.info(f"Odoo 19 has {len(names_19)} Vendor Bills.")
        
        # 3. Fetch Odoo 14 Vendor Bills
        logger.info("Fetching Odoo 14 Vendor Bills...")
        records_14 = models_14.execute_kw(DB_14, uid_14, PASS_14, 'account.move', 'search_read', 
            [[('move_type', '=', 'in_invoice'), ('state', '!=', 'cancel')]], 
            {'fields': ['name', 'state', 'invoice_date', 'ref', 'partner_id']})
        logger.info(f"Odoo 14 has {len(records_14)} Vendor Bills.")
        
        # 4. Categorize Missing
        missing_bills = []
        
        for r in records_14:
            name = r['name']
            
            # Skip draft if name is '/'? Odoo 14 draft bills might have '/'
            if name == '/':
                continue

            if name not in names_19:
                # Prepare row: Name, Ref, Partner, Date, State, Odoo14_ID
                partner = r['partner_id'][1] if r['partner_id'] else ''
                row = [name, r['ref'] or '', partner, r['invoice_date'], r['state'], r['id']]
                missing_bills.append(row)
                    
        logger.info(f"Found {len(missing_bills)} missing Vendor Bills.")
        
        # 5. Write CSV
        base_path = r"e:/odoo modules/19/metro/odoo14_to_19_migration"
        
        bill_file = os.path.join(base_path, "missing_vendor_bills.csv")
        with open(bill_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'ref', 'partner', 'date', 'state', 'odoo14_id']) # Header
            writer.writerows(missing_bills)
        logger.info(f"Generated: {bill_file}")
            
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    generate_missing_bills()
