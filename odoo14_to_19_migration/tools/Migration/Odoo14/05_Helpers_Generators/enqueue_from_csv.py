
import xmlrpc.client
import csv
import argparse
import logging

# Credentials
URL_19 = "https://metro.equdaierp.com"
DB_19 = "metrodb"
USER_19 = "admin"
PASS_19 = "Amaze@321"

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def enqueue_from_csv():
    try:
        # 1. Connect to Odoo 19
        logger.info("Connecting to Odoo 19...")
        common_19 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_19))
        uid_19 = common_19.authenticate(DB_19, USER_19, PASS_19, {})
        models_19 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_19))
        
        # 2. Get Config ID
        configs = models_19.execute_kw(DB_19, uid_19, PASS_19, 'odoo14.migration.config', 'search_read', [[], ['id', 'display_name']], {'limit': 1})
        if not configs:
            logger.error("No migration configuration found!")
            return
        config_id = configs[0]['id']
        logger.info(f"Using Migration Config: {configs[0]['display_name']} (ID: {config_id})")
        
        # 3. Process CSVs
        files = [
            ("e:/odoo modules/19/metro/odoo14_to_19_migration/missing_rfqs.csv", "RFQ"),
            ("e:/odoo modules/19/metro/odoo14_to_19_migration/missing_pos.csv", "PO")
        ]
        
        total_enqueued = 0
        
        for file_path, item_type in files:
            logger.info(f"\nProcessing {item_type} file: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
            if not rows:
                logger.info("  File is empty.")
                continue
                
            # Check for existing in queue to avoid duplicates
            names = [r['name'] for r in rows]
            existing = models_19.execute_kw(DB_19, uid_19, PASS_19, 'rfq.migration.line', 'search', 
                [[('uploaded_rfq_number', 'in', names)]])
            existing_recs = models_19.execute_kw(DB_19, uid_19, PASS_19, 'rfq.migration.line', 'read', 
                [existing], {'fields': ['uploaded_rfq_number']})
            existing_names = set(r['uploaded_rfq_number'] for r in existing_recs)
            
            to_create = []
            for r in rows:
                name = r['name']
                if name in existing_names:
                    # logger.info(f"  Skipping {name} (Already in queue)")
                    continue
                
                # Determine Stage based on state
                state = r['state']
                stage = "Draft"
                if state in ['purchase', 'done']:
                    stage = "Purchase Order"
                elif state == 'sent':
                    stage = "RFQ Sent"
                
                to_create.append({
                    'uploaded_rfq_number': name,
                    'status': 'pending_migration',
                    'excel_status': f'Missing {item_type} (Auto-Enqueued)',
                    'stage': stage,
                    'config_id': config_id,
                    'priority': 'Normal',
                    'company': 'Unknown' 
                })
            
            if to_create:
                logger.info(f"  Enqueueing {len(to_create)} items...")
                # Batch create
                batch_size = 50
                for i in range(0, len(to_create), batch_size):
                    batch = to_create[i:i+batch_size]
                    models_19.execute_kw(DB_19, uid_19, PASS_19, 'rfq.migration.line', 'create', [batch])
                total_enqueued += len(to_create)
            else:
                logger.info("  No new items to enqueue.")

        logger.info(f"\nTotal items enqueued: {total_enqueued}")

    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    enqueue_from_csv()
