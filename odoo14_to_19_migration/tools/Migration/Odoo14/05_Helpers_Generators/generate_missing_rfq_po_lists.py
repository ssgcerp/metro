
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

def generate_lists():
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
        
        # 2. Fetch Odoo 19 Names (Existing)
        logger.info("Fetching existing Odoo 19 records...")
        # Get ALL names to be safe
        existing_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order', 'search_read', 
            [[]], {'fields': ['name']})
        names_19 = set(r['name'] for r in existing_19)
        logger.info(f"Odoo 19 has {len(names_19)} POs/RFQs.")
        
        # 3. Fetch Odoo 14 Records
        logger.info("Fetching Odoo 14 records...")
        # We need name and state
        records_14 = models_14.execute_kw(DB_14, uid_14, PASS_14, 'purchase.order', 'search_read', 
            [[]], {'fields': ['name', 'state', 'date_order']})
        logger.info(f"Odoo 14 has {len(records_14)} POs/RFQs.")
        
        # 4. Categorize Missing
        missing_rfqs = []
        missing_pos = []
        
        rfq_states = ['draft', 'sent', 'to approve']
        po_states = ['purchase', 'done']
        
        for r in records_14:
            name = r['name']
            state = r['state']
            
            if name not in names_19:
                # Prepare row: Name, State, Date, Odoo14_ID
                row = [name, state, r['date_order'], r['id']]
                
                if state in rfq_states:
                    missing_rfqs.append(row)
                elif state in po_states:
                    missing_pos.append(row)
                    
        logger.info(f"Found {len(missing_rfqs)} missing RFQs.")
        logger.info(f"Found {len(missing_pos)} missing POs.")
        
        # 5. Write CSVs
        base_path = r"e:/odoo modules/19/metro/odoo14_to_19_migration"
        
        # RFQs
        rfq_file = os.path.join(base_path, "missing_rfqs.csv")
        with open(rfq_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'state', 'date_order', 'odoo14_id']) # Header
            writer.writerows(missing_rfqs)
        logger.info(f"Generated: {rfq_file}")
            
        # POs
        po_file = os.path.join(base_path, "missing_pos.csv")
        with open(po_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'state', 'date_order', 'odoo14_id']) # Header
            writer.writerows(missing_pos)
        logger.info(f"Generated: {po_file}")
            
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    generate_lists()
