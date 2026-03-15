import argparse
import json
import logging
import os
import sys
import pandas as pd
from datetime import datetime
import xmlrpc.client

# Setup logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '00_Logs_and_Reports')
os.makedirs(log_dir, exist_ok=True)
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = os.path.join(log_dir, f'auto_vendor_bill_migration_{timestamp}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class OdooClient:
    def __init__(self, config):
        self.url = config['url']
        self.db = config['db']
        self.username = config['username']
        self.password = config['password']
        self.uid = None
        self.models = None

    def authenticate(self):
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common', allow_none=True)
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            if self.uid:
                self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object', allow_none=True)
                return True
            return False
        except Exception as e:
            logger.error(f"Error authenticating to {self.url}: {e}")
            return False

    def execute(self, model, method, *args, **kwargs):
        if not self.uid:
            raise Exception("Not authenticated")
        return self.models.execute_kw(self.db, self.uid, self.password, model, method, args, kwargs)

def load_journal_mapping(excel_path):
    logger.info(f"Loading journal mapping from {excel_path}")
    try:
        df = pd.read_excel(excel_path)
        # Create a mapping dictionary: source_journal_id -> dest_journal_id
        mapping = {}
        for _, row in df.iterrows():
            if pd.notna(row['Source Journal ID']) and pd.notna(row['Dest Journal ID']):
                mapping[int(row['Source Journal ID'])] = int(row['Dest Journal ID'])
        logger.info(f"Loaded {len(mapping)} journal mappings.")
        return mapping
    except Exception as e:
        logger.error(f"Failed to load journal mapping: {e}")
        return {}

def main():
    parser = argparse.ArgumentParser(description="Auto Queue Vendor Bills for Migration")
    parser.add_argument('--config', default='migration_config.json', help='Path to config file')
    parser.add_argument('--mapping', default='..\\00_Logs_and_Reports\\journal_mapping_o14.xlsx', help='Path to journal mapping Excel')
    args = parser.parse_args()

    # Determine absolute paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, args.config)
    mapping_path = os.path.join(script_dir, args.mapping)

    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
        
    if not os.path.exists(mapping_path):
        logger.error(f"Mapping file not found: {mapping_path}")
        sys.exit(1)

    with open(config_path, 'r') as f:
        config = json.load(f)

    # 1. Authenticate
    o14 = OdooClient(config['odoo14'])
    o19 = OdooClient(config['odoo19'])

    logger.info("Authenticating with Odoo 14...")
    if not o14.authenticate():
        sys.exit(1)
    
    logger.info("Authenticating with Odoo 19...")
    if not o19.authenticate():
        sys.exit(1)

    # 2. Load Mapping
    journal_mapping = load_journal_mapping(mapping_path)

    # 3. Fetch Data
    logger.info("Fetching Posted Vendor Bills from Odoo 14...")
    # Fetching only posted 'in_invoice'
    o14_bills = o14.execute('account.move', 'search_read', 
        [('move_type', '=', 'in_invoice'), ('state', '=', 'posted')],
        fields=['name', 'journal_id', 'state', 'partner_id', 'company_id', 'amount_total', 'date']
    )
    logger.info(f"Found {len(o14_bills)} posted vendor bills in Odoo 14.")

    logger.info("Fetching Vendor Bills from Odoo 19 to compare...")
    o19_bills = o19.execute('account.move', 'search_read', 
        [('move_type', '=', 'in_invoice')],
        fields=['name', 'state']
    )
    o19_bill_names = {b['name'] for b in o19_bills}
    logger.info(f"Found {len(o19_bill_names)} vendor bills in Odoo 19.")

    # 4. Identify Missing Bills
    missing_bills = []
    for bill in o14_bills:
        if bill['name'] not in o19_bill_names:
            missing_bills.append(bill)

    logger.info(f"Identified {len(missing_bills)} missing bills to migrate.")

    if not missing_bills:
        logger.info("No missing bills. Exiting.")
        sys.exit(0)

    # 5. Export Report
    report_file = os.path.join(log_dir, f'missing_vendor_bills_report_{timestamp}.xlsx')
    df_missing = pd.DataFrame(missing_bills)
    
    # Clean up relational fields for Excel export
    if not df_missing.empty:
        if 'journal_id' in df_missing.columns:
            df_missing['journal_name'] = df_missing['journal_id'].apply(lambda x: x[1] if isinstance(x, list) and len(x) > 1 else str(x))
            df_missing['journal_id_num'] = df_missing['journal_id'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else None)
        if 'partner_id' in df_missing.columns:
            df_missing['partner_name'] = df_missing['partner_id'].apply(lambda x: x[1] if isinstance(x, list) and len(x) > 1 else str(x))
        if 'company_id' in df_missing.columns:
            df_missing['company_name'] = df_missing['company_id'].apply(lambda x: x[1] if isinstance(x, list) and len(x) > 1 else str(x))
            
    df_missing.to_excel(report_file, index=False)
    logger.info(f"Saved missing bills report to {report_file}")

    # 6. Queue Migration Lines in Odoo 19
    logger.info("Queuing missing bills into Odoo 19 vendor.bill.migration.line...")
    
    # We need to find the ID of the odoo14.migration.config record in Odoo 19 to attached to the lines
    config_ids = o19.execute('odoo14.migration.config', 'search', [], limit=1)
    migration_config_id = config_ids[0] if config_ids else False
    if not migration_config_id:
        logger.warning("No odoo14.migration.config found in Odoo 19. Migration lines might fail to check status natively, but they can still be processed.")

    queued_count = 0
    mapped_count = 0
    
    for bill in missing_bills:
        bill_number = bill['name']
            
        # Check if line already exists in queue
        existing_lines = o19.execute('vendor.bill.migration.line', 'search', [('uploaded_bill_number', '=', bill_number)])
        
        if existing_lines:
            # Update existing to Queued
            o19.execute('vendor.bill.migration.line', 'write', [existing_lines[0]], {
                'status': 'queued',
                'status_message': 'Auto-queued for migration',
            })
            queued_count += 1
        else:
            # Create new
            company_name = bill['company_id'][1] if isinstance(bill.get('company_id'), list) and len(bill['company_id']) > 1 else ''
            partner_name = bill['partner_id'][1] if isinstance(bill.get('partner_id'), list) and len(bill['partner_id']) > 1 else ''
            
            line_vals = {
                'uploaded_bill_number': bill_number,
                'status': 'queued',
                'status_message': 'Auto-queued for migration',
                'excel_status': bill.get('state', 'posted'),
                'company': company_name,
                'bill_partner_name': partner_name,
            }
            if migration_config_id:
                line_vals['config_id'] = migration_config_id
                
            if bill.get('date'):
                line_vals['invoice_bill_date'] = bill['date']
                
            o19.execute('vendor.bill.migration.line', 'create', [line_vals])
            queued_count += 1

    logger.info(f"Successfully queued {queued_count} bills for migration.")

if __name__ == "__main__":
    main()
