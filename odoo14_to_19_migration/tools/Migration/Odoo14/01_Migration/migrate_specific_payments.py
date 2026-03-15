import pandas as pd
import logging
import requests
import random
import os
import json
import ssl
import xmlrpc.client
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S',
                    handlers=[logging.FileHandler("specific_migration.log"), logging.StreamHandler()])
_logger = logging.getLogger(__name__)

# Odoo 14 Credentials (Source)
URL_14 = "https://erpmfs.com"
DB_14 = "metro_production_8_8_22"
USER_14 = "Sales.auh@metrofiresystems.com"
PASS_14 = "Sales@185734"

# Odoo 19 Credentials (Target)
URL_19 = "https://metro.equdaierp.com"
DB_19 = "newdb"
USER_19 = "admin"
PASS_19 = "Amaze@321"

MAIN_COMPANY_ID = 1

class OdooJsonRpcClient:
    def __init__(self, url, db, username, password):
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.uid = None

    def json_rpc(self, endpoint, params):
        data = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": params,
            "id": random.randint(0, 1000000000),
        }
        headers = {"Content-Type": "application/json"}
        try:
            response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers, timeout=300)
            res_json = response.json()
            if 'error' in res_json:
                _logger.error(f"RPC ERROR: {res_json['error']}")
            return res_json
        except Exception as e:
            _logger.error(f"RPC EXCEPTION: {e}")
            return None

    def authenticate(self):
        params = {"db": self.db, "login": self.username, "password": self.password}
        result = self.json_rpc("/web/session/authenticate", params)
        if result and 'result' in result and 'uid' in result['result']:
            self.uid = result['result']['uid']
            return True
        return False

    def execute_kw(self, model, method, args=None, kwargs=None):
        if args is None: args = []
        if kwargs is None: kwargs = {}
        params = {"model": model, "method": method, "args": args, "kwargs": kwargs}
        result = self.json_rpc("/web/dataset/call_kw", params)
        if result and 'error' in result:
             return None
        return result.get('result')

def reconcile_payment(client, payment_id, partner_id, invoice_company_id):
    try:
        payment = client.execute_kw('account.payment', 'read', [[payment_id], ['move_id', 'name', 'memo']])
        if not payment: return
        move_field = payment[0].get('move_id')
        if not move_field: return
        move_id = move_field[0]

        # Use search_read on account.move.line to find the receivable line of the payment (in Company 1)
        pay_lines = client.execute_kw('account.move.line', 'search_read', 
            [[('move_id', '=', move_id), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]],
            {'fields': ['id', 'credit']}
        )
        if not pay_lines: return
        payment_line_id = pay_lines[0]['id']
        
        memo = payment[0].get('memo')
        if memo:
            # Find invoice across companies
            invs = client.execute_kw('account.move', 'search_read', 
                [[('name', '=', memo), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('payment_state', '!=', 'paid'), ('company_id', '=', invoice_company_id)]], 
                {'fields': ['id']}
            )
            if invs:
                inv_lines = client.execute_kw('account.move.line', 'search_read', 
                    [[('move_id', '=', invs[0]['id']), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]],
                    {'fields': ['id']}
                )
                if inv_lines:
                    client.execute_kw('account.move.line', 'reconcile', [[payment_line_id, inv_lines[0]['id']]])
                    _logger.info(f"   Reconciled {payment[0]['name']} with Invoice {memo}")
                    return True
    except Exception as e:
        _logger.error(f"   Reconciliation failed for payment {payment_id}: {e}")
    return False

def get_dest_journal(dest_client, mapping_df, dest_company_name, o14_journal_name, pay_name):
    # Search consistently in MAIN_COMPANY_ID (1)
    
    # 1. Try mapping file
    m = mapping_df[(mapping_df['Dest Company'] == dest_company_name) & (mapping_df['Source Journal Name'] == o14_journal_name)]
    if not m.empty:
        dest_journal_name = m.iloc[0]['Dest Journal Name']
        ids = dest_client.execute_kw('account.journal', 'search', [[('name', '=', dest_journal_name), ('company_id', '=', MAIN_COMPANY_ID)]])
        if ids: return ids[0]

    # 2. Try direct name match in company 1
    ids = dest_client.execute_kw('account.journal', 'search', [[('name', '=', o14_journal_name), ('company_id', '=', MAIN_COMPANY_ID)]])
    if ids: return ids[0]

    # 3. Try partial name match in company 1
    ids = dest_client.execute_kw('account.journal', 'search', [[('name', 'ilike', o14_journal_name), ('company_id', '=', MAIN_COMPANY_ID)]])
    if ids: return ids[0]

    # 4. Fallback by type in company 1
    j_type = 'bank'
    if pay_name.startswith('CSH'):
        j_type = 'cash'
    
    ids = dest_client.execute_kw('account.journal', 'search', [[('type', '=', j_type), ('company_id', '=', MAIN_COMPANY_ID)]], {'limit': 1})
    if ids: return ids[0]

    return False

def main():
    mapping_file = "journal_mapping_o14.xlsx"
    if not os.path.exists(mapping_file):
        _logger.error(f"Mapping file {mapping_file} not found.")
        return
    
    mapping_df = pd.read_excel(mapping_file)
    
    specific_file = "specific_payments_to_migrate.txt"
    if not os.path.exists(specific_file):
        _logger.error(f"Specific list file {specific_file} not found.")
        return
        
    with open(specific_file, "r") as f:
        pay_names = [name.strip() for name in f if name.strip()]

    # Source Connection (XML-RPC)
    common_14 = xmlrpc.client.ServerProxy(f"{URL_14}/xmlrpc/2/common", context=ssl._create_unverified_context())
    uid_14 = common_14.authenticate(DB_14, USER_14, PASS_14, {})
    models_14 = xmlrpc.client.ServerProxy(f"{URL_14}/xmlrpc/2/object", context=ssl._create_unverified_context())

    # Target Connection (JSON-RPC)
    dest_client = OdooJsonRpcClient(URL_19, DB_19, USER_19, PASS_19)
    if not dest_client.authenticate():
        _logger.error("Failed to authenticate with Odoo 19.")
        return

    _logger.info(f"Migrating {len(pay_names)} specific payments via Company 1 standard...")

    count = 0
    for name in pay_names:
        _logger.info(f"Processing {name}...")
        
        # Check Duplicate in Target
        if dest_client.execute_kw('account.move', 'search_count', [[('name', '=', name)]]) > 0:
            _logger.info(f"   Already exists in Odoo 19. Skipping.")
            continue
            
        # Search in Source
        pays_14 = models_14.execute_kw(DB_14, uid_14, PASS_14, 'account.payment', 'search_read',
            [[('name', '=', name)]],
            {'fields': ['name', 'amount', 'date', 'partner_id', 'journal_id', 'ref', 'company_id', 'payment_type', 'partner_type']}
        )
        
        if not pays_14:
            _logger.warning(f"   No payment found in Odoo 14 for name {name}.")
            continue
            
        p = pays_14[0]
        o14_journal_name = p['journal_id'][1]
        invoice_ref = p['ref']
        
        invoice_company_id = False
        invoice_company_name = False
        
        if invoice_ref:
            inv_search_name = invoice_ref
            if "Inv #" in invoice_ref:
                inv_search_name = invoice_ref.split("Inv #")[-1].strip()
            
            # _logger.info(f"   Searching Odoo 19 invoice: {inv_search_name}")
            invs = dest_client.execute_kw('account.move', 'search_read', 
                [[('name', 'ilike', inv_search_name), ('move_type', '=', 'out_invoice')]], 
                {'fields': ['company_id', 'partner_id'], 'limit': 1}
            )
            if invs:
                invoice_company_id = invs[0]['company_id'][0]
                invoice_company_name = invs[0]['company_id'][1]
                _logger.info(f"   Found Invoice in Company: {invoice_company_name}")
            else:
                _logger.warning(f"   Invoice '{inv_search_name}' not found. Defaulting mapping logic.")
                if name.startswith('BNK8'): invoice_company_name = 'FUJAIRAH'
                elif name.startswith('BNK1'): invoice_company_name = 'ABU DHABI'
                else: invoice_company_name = 'ABU DHABI'
        else:
            _logger.warning(f"   No reference/memo found for {name}. Skipping.")
            continue

        # Resolve Journal in MAIN COMPANY
        dest_journal_id = get_dest_journal(dest_client, mapping_df, invoice_company_name, o14_journal_name, name)
        if not dest_journal_id:
            _logger.error(f"   Could not find suitable journal in Metro Fire for O14 journal '{o14_journal_name}'.")
            continue
        
        # Get Destination Partner ID
        partner_name = p['partner_id'][1]
        partner_ids = dest_client.execute_kw('res.partner', 'search', [[('name', '=', partner_name)]])
        if not partner_ids:
             _logger.warning(f"   Partner '{partner_name}' not found in Odoo 19.")
             continue
        dest_partner_id = partner_ids[0]
        
        # Create Payment in Target (COMPANY 1)
        try:
            val = {
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': dest_partner_id,
                'amount': p['amount'],
                'date': p['date'],
                'journal_id': dest_journal_id,
                'company_id': MAIN_COMPANY_ID,
                'memo': invoice_ref or name,
            }
            
            new_pay_id = dest_client.execute_kw('account.payment', 'create', [val])
            if new_pay_id:
                # Post Payment
                dest_client.execute_kw('account.payment', 'action_post', [[new_pay_id]])
                
                # Force Name
                dest_client.execute_kw('account.payment', 'write', [[new_pay_id], {'name': name}])
                payment_read = dest_client.execute_kw('account.payment', 'read', [[new_pay_id], ['move_id']])
                if payment_read and payment_read[0]['move_id']:
                    dest_client.execute_kw('account.move', 'write', [[payment_read[0]['move_id'][0]], {'name': name}])
                
                _logger.info(f"   Successfully migrated {name} to Odoo 19 (via Company 1).")
                
                # Reconcile if invoice was found
                if invoice_company_id:
                    reconcile_payment(dest_client, new_pay_id, dest_partner_id, invoice_company_id)
                count += 1
        except Exception as e:
            _logger.error(f"   Failed to create/post payment {name}: {e}")

    _logger.info(f"Migration finished. Total migrated: {count}")

if __name__ == "__main__":
    main()
