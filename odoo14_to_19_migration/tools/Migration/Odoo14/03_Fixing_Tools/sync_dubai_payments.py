import pandas as pd
import xmlrpc.client
import ssl
import time
import logging
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s', 
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler("sync_dubai.log"),
        logging.StreamHandler()
    ]
)
_logger = logging.getLogger(__name__)

# Configuration
URL = 'https://metro.equdaierp.com'
SRC_DB = 'metrodb'
DEST_DB = 'newdb'
USER = 'admin'
PWD = 'Amaze@321'
EXCEL_PATH = r"e:\odoo modules\19\metro\odoo14_to_19_migration\tools\Docs\Payments (account.payment) (1).xlsx"
COMPANY_NAME = 'DUBAI'
MAPPING_FILE = 'journal_mapping_template.xlsx'

def get_odoo_client(url, db, user, pwd):
    # Use a long timeout for creation/deletion
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context(), allow_none=True)
    uid = common.authenticate(db, user, pwd, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context(), allow_none=True)
    return uid, models

def main():
    _logger.info("Starting sync process...")
    
    # 1. Load Excel Data
    _logger.info(f"Loading Excel file: {EXCEL_PATH}")
    try:
        df_excel = pd.read_excel(EXCEL_PATH)
        excel_names = set(df_excel['Number'].astype(str).unique())
        _logger.info(f"Excel contains {len(excel_names)} unique payment numbers.")
    except Exception as e:
        _logger.error(f"Failed to load Excel: {e}")
        return

    # 2. Load Journal Mappings
    _logger.info(f"Loading Journal mappings: {MAPPING_FILE}")
    try:
        df_map = pd.read_excel(MAPPING_FILE)
        journal_map = {}
        for _, row in df_map.iterrows():
            if str(row['Source Company']) == COMPANY_NAME:
                journal_map[int(row['Source Journal ID'])] = {
                    'dest_journal_id': int(row['Dest Journal ID']),
                    'dest_company_name': str(row['Dest Company'])
                }
    except Exception as e:
        _logger.error(f"Failed to load Journal Mappings: {e}")
        return

    # 3. Connect to Odoo
    try:
        src_uid, src_models = get_odoo_client(URL, SRC_DB, USER, PWD)
        dest_uid, dest_models = get_odoo_client(URL, DEST_DB, USER, PWD)
    except Exception as e:
        _logger.error(f"Failed to connect to Odoo: {e}")
        return

    if not src_uid or not dest_uid:
        _logger.error("Authentication failed.")
        return

    # 4. Resolve Company IDs
    try:
        src_company_id = src_models.execute_kw(SRC_DB, src_uid, PWD, 'res.company', 'search', [[('name', '=', COMPANY_NAME)]])[0]
        dest_company_id = dest_models.execute_kw(DEST_DB, dest_uid, PWD, 'res.company', 'search', [[('name', '=', COMPANY_NAME)]])[0]
    except Exception as e:
        _logger.error(f"Failed to resolve company IDs: {e}")
        return

    # 5. Identify and Cleanup Extras in newdb
    _logger.info("Step 1: Cleanup extras in newdb...")
    dest_domain = [
        ('company_id', '=', dest_company_id),
        ('partner_type', '=', 'customer'),
        ('payment_type', '=', 'inbound')
    ]
    try:
        dest_pays = dest_models.execute_kw(DEST_DB, dest_uid, PWD, 'account.payment', 'search_read', [dest_domain], {'fields': ['id', 'name']})
        _logger.info(f"Total payments currently in NewDB for DUBAI: {len(dest_pays)}")
        
        deleted_count = 0
        for p in dest_pays:
            if p['name'] not in excel_names:
                _logger.info(f"  Deleting extra/mismatched payment: {p['name']} (ID: {p['id']})")
                try:
                    # Cancel and delete
                    try: dest_models.execute_kw(DEST_DB, dest_uid, PWD, 'account.payment', 'action_draft', [[p['id']]])
                    except: pass
                    try: dest_models.execute_kw(DEST_DB, dest_uid, PWD, 'account.payment', 'action_cancel', [[p['id']]])
                    except: pass
                    dest_models.execute_kw(DEST_DB, dest_uid, PWD, 'account.payment', 'unlink', [[p['id']]])
                    deleted_count += 1
                except Exception as e:
                    _logger.warning(f"    Failed to delete {p['name']}: {e}")
        _logger.info(f"Successfully deleted {deleted_count} extra payments.")
    except Exception as e:
        _logger.error(f"Cleanup failed: {e}")

    # 6. Identify Missing Payments
    _logger.info("Step 2: Identifying missing payments...")
    try:
        final_dest_pays = dest_models.execute_kw(DEST_DB, dest_uid, PWD, 'account.payment', 'search_read', [dest_domain], {'fields': ['name']})
        final_dest_names = set(p['name'] for p in final_dest_pays)
        missing_names = [name for name in excel_names if name not in final_dest_names]
        _logger.info(f"Need to migrate {len(missing_names)} missing payments.")
    except Exception as e:
        _logger.error(f"Failed to identify missing: {e}")
        return

    if not missing_names:
        _logger.info("Everything is in sync.")
        return

    # 7. Migrate Missing
    _logger.info("Step 3: Migrating missing payments...")
    batch_size = 50 # Smaller batch for safety
    for i in range(0, len(missing_names), batch_size):
        batch = missing_names[i:i + batch_size]
        _logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} records)...")
        
        try:
            src_pays = src_models.execute_kw(SRC_DB, src_uid, PWD, 'account.payment', 'search_read', 
                [[('name', 'in', batch), ('company_id', '=', src_company_id)]], 
                {'fields': ['name', 'date', 'amount', 'partner_id', 'journal_id', 'currency_id', 'memo', 'state']}
            )
        except Exception as e:
            _logger.error(f"Failed to fetch batch from source: {e}")
            continue

        for pay in src_pays:
            pay_name = pay['name']
            src_j_id = pay['journal_id'][0]
            
            if src_j_id not in journal_map:
                _logger.warning(f"  Skipping {pay_name}: Journal {pay['journal_id'][1]} not mapped.")
                continue

            # Map Partner
            src_partner_name = pay['partner_id'][1] if pay['partner_id'] else ''
            try:
                dest_partner_search = dest_models.execute_kw(DEST_DB, dest_uid, PWD, 'res.partner', 'search', [[('name', '=', src_partner_name)]], {'limit': 1})
                if not dest_partner_search:
                    _logger.warning(f"  Skipping {pay_name}: Partner '{src_partner_name}' not found.")
                    continue
                dest_partner_id = dest_partner_search[0]
            except Exception as e:
                _logger.error(f"  Partner search failed for {pay_name}: {e}")
                continue

            vals = {
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': dest_partner_id,
                'amount': pay['amount'],
                'date': pay['date'],
                'name': pay_name,
                'journal_id': journal_map[src_j_id]['dest_journal_id'],
                'company_id': dest_company_id,
                'memo': pay.get('memo', '')
            }

            try:
                new_payment_id = dest_models.execute_kw(DEST_DB, dest_uid, PWD, 'account.payment', 'create', [vals])
                _logger.info(f"  Created: {pay_name}")

                if pay['state'] != 'draft':
                    try:
                        dest_models.execute_kw(DEST_DB, dest_uid, PWD, 'account.payment', 'action_post', [[new_payment_id]])
                        _logger.info(f"    Posted: {pay_name}")
                    except Exception as post_e:
                        _logger.warning(f"    Failed to post {pay_name}: {post_e}")
                else:
                    _logger.info(f"    (Left as Draft)")
            except Exception as create_e:
                _logger.error(f"  Failed to create {pay_name}: {create_e}")

        time.sleep(1) # Slow down slightly to prevent overloading rpc

    _logger.info("Sync completed.")

if __name__ == "__main__":
    main()
