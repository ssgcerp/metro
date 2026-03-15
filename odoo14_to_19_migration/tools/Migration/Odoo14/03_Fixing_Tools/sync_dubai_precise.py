import pandas as pd
import xmlrpc.client
import ssl
import time
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s', 
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler("sync_dubai_precise.log"),
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
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context(), allow_none=True)
    uid = common.authenticate(db, user, pwd, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context(), allow_none=True)
    return uid, models

def reconcile_and_clear(models, db, uid, pwd, payment_id, partner_id):
    try:
        payment = models.execute_kw(db, uid, pwd, 'account.payment', 'read', [[payment_id], ['move_id', 'name', 'memo', 'amount', 'date', 'journal_id', 'currency_id']])
        if not payment: return
        p = payment[0]
        payment_name = p['name']
        move_id = p['move_id'][0] if p.get('move_id') else False
        
        if not move_id: return

        # 1. Reconcile to Invoice
        raw_memo = p.get('memo', '')
        if raw_memo:
            memo_parts = [m.strip() for m in str(raw_memo).split(',')]
            pay_lines = models.execute_kw(db, uid, pwd, 'account.move.line', 'search_read', 
                [[('move_id', '=', move_id), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]],
                {'fields': ['id']}
            )
            
            if pay_lines:
                for memo in memo_parts:
                    if not memo: continue
                    inv_domain = [
                        ('move_type', '=', 'out_invoice'), ('partner_id', '=', partner_id), ('state', '=', 'posted'), 
                        ('payment_state', 'in', ['not_paid', 'partial']), 
                        '|', ('name', '=', memo), ('name', '=ilike', '%' + memo)
                    ]
                    invs = models.execute_kw(db, uid, pwd, 'account.move', 'search_read', [inv_domain], {'fields': ['id', 'name']})
                    if invs:
                        inv_lines = models.execute_kw(db, uid, pwd, 'account.move.line', 'search_read', 
                            [[('move_id', '=', invs[0]['id']), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]],
                            {'fields': ['id']}
                        )
                        if inv_lines:
                            try:
                                models.execute_kw(db, uid, pwd, 'account.move.line', 'reconcile', [[pay_lines[0]['id'], inv_lines[0]['id']]])
                                _logger.info(f"    Reconciled {payment_name} with {invs[0]['name']}")
                            except: pass

        # 2. Mark as PAID (Clear with Bank)
        journal_id = p['journal_id'][0]
        journal_data = models.execute_kw(db, uid, pwd, 'account.journal', 'read', [[journal_id], ['default_account_id']])
        if not journal_data or not journal_data[0]['default_account_id']: return
        bank_account_id = journal_data[0]['default_account_id'][0]
        
        liquidity_lines = models.execute_kw(db, uid, pwd, 'account.move.line', 'search_read', 
            [[('move_id', '=', move_id), ('reconciled', '=', False), ('account_id.account_type', '!=', 'asset_receivable')]],
            {'fields': ['id', 'account_id']}
        )
        if not liquidity_lines: return
        liquidity_line = liquidity_lines[0]
        outstanding_account_id = liquidity_line['account_id'][0]
        
        if bank_account_id == outstanding_account_id: return

        clearance_move_vals = {
            'journal_id': journal_id, 'date': p['date'], 'move_type': 'entry',
            'line_ids': [
                (0, 0, {'account_id': bank_account_id, 'name': f"Bank Clearance - {payment_name}", 'debit': p['amount'], 'credit': 0.0, 'currency_id': p['currency_id'][0]}),
                (0, 0, {'account_id': outstanding_account_id, 'name': f"Clearance - {payment_name}", 'debit': 0.0, 'credit': p['amount'], 'currency_id': p['currency_id'][0]})
            ]
        }
        clear_id = models.execute_kw(db, uid, pwd, 'account.move', 'create', [clearance_move_vals])
        models.execute_kw(db, uid, pwd, 'account.move', 'action_post', [[clear_id]])
        
        clear_lines = models.execute_kw(db, uid, pwd, 'account.move.line', 'search_read', [[('move_id', '=', clear_id), ('account_id', '=', outstanding_account_id)]], {'fields': ['id']})
        if clear_lines:
            try:
                models.execute_kw(db, uid, pwd, 'account.move.line', 'reconcile', [[liquidity_line['id'], clear_lines[0]['id']]])
                _logger.info(f"    Marked as PAID (Bank Cleared)")
            except: pass
    except Exception as e:
        if "marshal None" not in str(e):
            _logger.warning(f"  Reconciliation/Clearance error: {e}")

def main():
    _logger.info("Starting precise DUBAI sync...")
    
    # 1. Load Excel Data
    df_excel = pd.read_excel(EXCEL_PATH)
    excel_names = df_excel['Number'].astype(str).tolist()
    _logger.info(f"Excel contains {len(excel_names)} payments.")

    # 2. Load Journal Mappings
    df_map = pd.read_excel(MAPPING_FILE)
    journal_map = {}
    for _, row in df_map.iterrows():
        if str(row['Source Company']) == COMPANY_NAME:
            journal_map[int(row['Source Journal ID'])] = int(row['Dest Journal ID'])

    # 3. Connect to Odoo
    src_uid, src_models = get_odoo_client(URL, SRC_DB, USER, PWD)
    dest_uid, dest_models = get_odoo_client(URL, DEST_DB, USER, PWD)

    # 4. Resolve Company ID
    dest_company_id = dest_models.execute_kw(DEST_DB, dest_uid, PWD, 'res.company', 'search', [[('name', '=', COMPANY_NAME)]])[0]

    # 5. Process EACH payment from Excel
    for name in excel_names:
        _logger.info(f"Processing: {name}")
        
        # Check if already exists in dest
        exists = dest_models.execute_kw(DEST_DB, dest_uid, PWD, 'account.payment', 'search', [[('name', '=', name), ('company_id', '=', dest_company_id)]])
        if exists:
            _logger.info(f"  {name} already exists. Attempting reconciliation...")
            # Still try to reconcile in case it was created but not linked
            pay_read = dest_models.execute_kw(DEST_DB, dest_uid, PWD, 'account.payment', 'read', [exists, ['partner_id', 'state']])
            if pay_read and pay_read[0]['state'] == 'in_process':
                reconcile_and_clear(dest_models, DEST_DB, dest_uid, PWD, exists[0], pay_read[0]['partner_id'][0])
            continue

        # Fetch from Source
        src_pays = src_models.execute_kw(SRC_DB, src_uid, PWD, 'account.payment', 'search_read', [[('name', '=', name)]], 
            {'fields': ['date', 'amount', 'partner_id', 'journal_id', 'currency_id', 'memo', 'state']})
        
        if not src_pays:
            _logger.warning(f"  {name} not found in Source MetroDB.")
            continue
        
        pay = src_pays[0]
        src_j_id = pay['journal_id'][0]
        if src_j_id not in journal_map:
            _logger.warning(f"  Journal {pay['journal_id'][1]} not mapped.")
            continue
            
        # Partner Mapping
        src_partner_name = pay['partner_id'][1] if pay['partner_id'] else ''
        dest_partner_search = dest_models.execute_kw(DEST_DB, dest_uid, PWD, 'res.partner', 'search', [[('name', '=', src_partner_name)]], {'limit': 1})
        if not dest_partner_search:
            _logger.warning(f"  Partner '{src_partner_name}' not found.")
            continue
        dest_partner_id = dest_partner_search[0]

        vals = {
            'payment_type': 'inbound', 'partner_type': 'customer', 'partner_id': dest_partner_id,
            'amount': pay['amount'], 'date': pay['date'], 'name': name,
            'journal_id': journal_map[src_j_id], 'company_id': dest_company_id, 'memo': pay.get('memo', '')
        }

        try:
            new_id = dest_models.execute_kw(DEST_DB, dest_uid, PWD, 'account.payment', 'create', [vals])
            
            # FORCE NAME if Odoo rename it
            new_read = dest_models.execute_kw(DEST_DB, dest_uid, PWD, 'account.payment', 'read', [[new_id], ['name']])
            if new_read[0]['name'] != name:
                _logger.info(f"  Odoo renamed to {new_read[0]['name']}. Forcing back to {name}...")
                dest_models.execute_kw(DEST_DB, dest_uid, PWD, 'account.payment', 'write', [[new_id], {'name': name}])

            _logger.info(f"  Created: {name}")

            if pay['state'] != 'draft':
                try:
                    dest_models.execute_kw(DEST_DB, dest_uid, PWD, 'account.payment', 'action_post', [[new_id]])
                    _logger.info(f"  Posted: {name}")
                    # Reconcile
                    reconcile_and_clear(dest_models, DEST_DB, dest_uid, PWD, new_id, dest_partner_id)
                except Exception as post_e:
                    _logger.warning(f"  Post failed: {post_e}")
            else:
                _logger.info(f"  (Left as Draft)")
        except Exception as e:
            _logger.error(f"  Create failed for {name}: {e}")

    _logger.info("Precise sync completed.")

if __name__ == "__main__":
    main()
