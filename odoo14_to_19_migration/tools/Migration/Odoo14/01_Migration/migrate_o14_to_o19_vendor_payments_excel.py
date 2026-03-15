import pandas as pd
import argparse
import logging
import time
import requests
import random
import os
import json
import ssl
import xmlrpc.client
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
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

def reconcile_payment(client, payment_id, partner_id, dest_company_id):
    try:
        payment = client.execute_kw('account.payment', 'read', [[payment_id], ['move_id', 'name', 'memo']])
        if not payment: return
        move_field = payment[0].get('move_id')
        if not move_field: return
        move_id = move_field[0]

        # Vendor Payment: Look for debit line on Payable account
        pay_lines = client.execute_kw('account.move.line', 'search_read', 
            [[('move_id', '=', move_id), ('account_id.account_type', '=', 'liability_payable'), ('reconciled', '=', False)]],
            {'fields': ['id', 'debit']}
        )
        if not pay_lines: return
        payment_line_id = pay_lines[0]['id']
        payment_amount = pay_lines[0]['debit']

        matched_line_id = False
        memo = payment[0].get('memo')
        
        if memo:
            # Vendor Bill: Look for posted invoice with matching name or ref
            invs = client.execute_kw('account.move', 'search_read', 
                [[('move_type', '=', 'in_invoice'), ('state', '=', 'posted'), ('payment_state', '!=', 'paid'), ('company_id', '=', dest_company_id), '|', ('name', '=', memo), ('ref', '=', memo)]], 
                {'fields': ['id']}
            )
            if invs:
                inv_lines = client.execute_kw('account.move.line', 'search_read', 
                    [[('move_id', '=', invs[0]['id']), ('account_id.account_type', '=', 'liability_payable'), ('reconciled', '=', False)]],
                    {'fields': ['id']}
                )
                if inv_lines: matched_line_id = inv_lines[0]['id']

        if not matched_line_id and partner_id:
            # Open Payable lines
            open_lines = client.execute_kw('account.move.line', 'search_read', 
                [[('parent_state', '=', 'posted'), ('account_id.account_type', '=', 'liability_payable'), ('partner_id', '=', partner_id), ('reconciled', '=', False), ('move_id.move_type', '=', 'in_invoice'), ('company_id', '=', dest_company_id), ('credit', '>', 0)]], 
                {'fields': ['id', 'credit']}
            )
            if open_lines:
                for line in open_lines:
                    if abs(line['credit'] - payment_amount) < 0.01:
                        matched_line_id = line['id']
                        break
        
        if matched_line_id:
            client.execute_kw('account.move.line', 'reconcile', [[payment_line_id, matched_line_id]])
            _logger.info(f"  Reconciled successfully")
    except Exception as e:
        _logger.error(f"  Reconciliation failed: {e}")

def mark_payment_as_cleared(client, payment_id):
    try:
        pay_data = client.execute_kw('account.payment', 'read', [[payment_id], ['move_id', 'journal_id', 'date', 'amount', 'currency_id', 'name']])
        if not pay_data: return
        move_id = pay_data[0]['move_id'][0] if pay_data[0].get('move_id') else False
        journal_id = pay_data[0]['journal_id'][0] if pay_data[0].get('journal_id') else False
        payment_date = pay_data[0]['date']
        amount = pay_data[0]['amount']
        curr_field = pay_data[0].get('currency_id')
        currency_id = curr_field[0] if curr_field else False
        payment_name = pay_data[0].get('name')

        if not move_id or not journal_id: return

        # For vendor payments (outbound), the liquidity line is usually Credit to Outstanding Payments
        lines = client.execute_kw('account.move.line', 'search_read', 
            [[('move_id', '=', move_id), ('reconciled', '=', False), ('account_id.account_type', '!=', 'asset_receivable'), ('account_id.account_type', '!=', 'liability_payable')]],
            {'fields': ['id', 'account_id', 'debit', 'credit', 'name']}
        )
        if not lines: return
        liquidity_line = lines[0]
        outstanding_account_id = liquidity_line['account_id'][0]
        journal_data = client.execute_kw('account.journal', 'read', [[journal_id], ['default_account_id']])
        if not journal_data or not journal_data[0]['default_account_id']: return
        bank_account_id = journal_data[0]['default_account_id'][0]
        if bank_account_id == outstanding_account_id: return

        # Vendor (Outbound) Clearance: Debit Outstanding, Credit Bank
        clearance_move_vals = {
            'journal_id': journal_id,
            'date': payment_date,
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {
                    'account_id': outstanding_account_id,
                    'name': f"Clearance - {payment_name}",
                    'debit': amount,
                    'credit': 0.0,
                    'currency_id': currency_id,
                }),
                (0, 0, {
                    'account_id': bank_account_id,
                    'name': f"Bank Clearance - {payment_name}",
                    'debit': 0.0,
                    'credit': amount,
                    'currency_id': currency_id,
                })
            ]
        }
        clearance_move_id = client.execute_kw('account.move', 'create', [clearance_move_vals])
        client.execute_kw('account.move', 'action_post', [[clearance_move_id]])
        clearance_lines = client.execute_kw('account.move.line', 'search_read', 
            [[('move_id', '=', clearance_move_id), ('account_id', '=', outstanding_account_id)]],
            {'fields': ['id']}
        )
        if clearance_lines:
            client.execute_kw('account.move.line', 'reconcile', [[liquidity_line['id'], clearance_lines[0]['id']]])
            _logger.info(f"  Payment marked as fully PAID.")
    except Exception as e:
        _logger.warning(f"  Failed clearance: {e}")

def main():
    parser = argparse.ArgumentParser(description='Migrate Odoo 14 Vendor Payments to 19 via Excel Map')
    parser.add_argument('--company-name', required=True, help='Source Company (Branch) Name in Odoo 14')
    parser.add_argument('--excel-map', required=True, help='Path to Excel mapping file')
    parser.add_argument('--limit', type=int, default=100, help='Batch size')
    args = parser.parse_args()

    if not os.path.exists(args.excel_map):
        _logger.error(f"Excel mapping file '{args.excel_map}' not found.")
        return

    # 1. Load Journal Map
    try:
        df_map = pd.read_excel(args.excel_map)
        journal_map = {}
        global_map = {}
        for _, row in df_map.iterrows():
            src_j_id = int(row['Source Journal ID'])
            dest_j_id = row['Dest Journal ID']
            if not pd.isna(dest_j_id):
                global_map[src_j_id] = int(dest_j_id)
                if str(row['Source Company']).strip() == args.company_name.strip():
                    journal_map[src_j_id] = int(dest_j_id)
        
        # Add a global fallback for missing journal IDs
        for j_id, dest_j in global_map.items():
            if j_id not in journal_map:
                journal_map[j_id] = dest_j
        
        if not journal_map:
            _logger.error(f"No valid journal mappings found for '{args.company_name}' in Excel.")
            return
    except Exception as e:
        _logger.error(f"Failed to load Excel map: {e}")
        return

    # 2. Connect
    src_ctx = ssl._create_unverified_context()
    src_common = xmlrpc.client.ServerProxy(f'{URL_14}/xmlrpc/2/common', context=src_ctx)
    src_uid = src_common.authenticate(DB_14, USER_14, PASS_14, {})
    src_models = xmlrpc.client.ServerProxy(f'{URL_14}/xmlrpc/2/object', context=src_ctx)
    
    dest_client = OdooJsonRpcClient(URL_19, DB_19, USER_19, PASS_19)
    if not src_uid or not dest_client.authenticate():
        _logger.error("Authentication failed.")
        return
    _logger.info("Connected to Source and Target.")

    # 3. Migration Loop
    offset = 0
    migration_logs = []
    
    try:
        while True:
            _logger.info(f"Fetching batch (Offset: {offset}, Limit: {args.limit})...")
            domain = [
                ('payment_type', '=', 'outbound'),
                ('partner_type', '=', 'supplier'),
                ('branch_id.name', '=', args.company_name),
                ('state', 'in', ['draft', 'posted'])
            ]
            
            try:
                payments = src_models.execute_kw(DB_14, src_uid, PASS_14, 'account.payment', 'search_read', [domain], 
                    {'fields': ['name', 'date', 'amount', 'partner_id', 'journal_id', 'ref', 'state', 'reconciled_bill_ids', 'reconciled_invoice_ids'], 
                     'limit': args.limit, 'offset': offset, 'order': 'date asc'})
                if not payments: break
            except Exception as e:
                _logger.error(f"Fetch failed: {e}")
                break

            for pay in payments:
                pay_name = pay['name']
                src_j_id = pay['journal_id'][0]
                memo = pay.get('ref') or pay['name']
                
                log_entry = {
                    'Name': pay_name, 'Date': pay['date'], 'Amount': pay['amount'], 
                    'Status': 'Skipped', 'Message': ''
                }

                if src_j_id not in journal_map:
                    log_entry['Message'] = f"Journal ID {src_j_id} not mapped in Excel even with fallback."
                    migration_logs.append(log_entry)
                    continue

                # Check Duplicate in account.move (more reliable in Odoo 19)
                if dest_client.execute_kw('account.move', 'search_count', [[('name', '=', pay_name)]]) > 0:
                    log_entry['Message'] = "Already exists (Move name matched)."
                    migration_logs.append(log_entry)
                    continue

                # Fallback: check account.payment just in case
                if dest_client.execute_kw('account.payment', 'search_count', [[('name', '=', pay_name)]]) > 0:
                    log_entry['Message'] = "Already exists (Payment name matched)."
                    migration_logs.append(log_entry)
                    continue

                try:
                    # Dynamic Company Detection
                    dest_company_id = 1 # Fallback
                    dest_partner_id = False
                    
                    # 1. First, find correct Company Fallback based on param
                    company_search = dest_client.execute_kw('res.company', 'search_read', [[('name', '=', args.company_name)]], {'fields': ['id'], 'limit': 1})
                    if company_search:
                        dest_company_id = company_search[0]['id']
                        
                    inv_search = False
                    
                    # 2. Get exact invoice linkage from Odoo 14
                    bill_ids = pay.get('reconciled_bill_ids') or pay.get('reconciled_invoice_ids') or []
                    if bill_ids:
                        o14_bills = src_models.execute_kw(DB_14, src_uid, PASS_14, 'account.move', 'read', [bill_ids], {'fields': ['name']})
                        if o14_bills and o14_bills[0].get('name'):
                            exact_bill_name = o14_bills[0]['name']
                            
                            # 3. Search Odoo 19 for this exact bill name IN this exact company
                            inv_search = dest_client.execute_kw('account.move', 'search_read', 
                                [[('move_type', 'in', ['in_invoice', 'in_receipt', 'out_invoice']), ('name', '=', exact_bill_name), ('company_id', '=', dest_company_id)]], 
                                {'fields': ['company_id', 'partner_id', 'name'], 'limit': 1})
                    
                    if inv_search:
                        dest_partner_id = inv_search[0]['partner_id'][0]
                        _logger.info(f"  Found exact linked bill {inv_search[0]['name']} in Company {inv_search[0]['company_id'][1]}")
                    else:
                        # Fallback partner mapping if no bill is linked
                        src_p_name = pay['partner_id'][1]
                        p_search = dest_client.execute_kw('res.partner', 'search', [[('name', '=', src_p_name)]], {'limit': 1})
                        if p_search: dest_partner_id = p_search[0]
                            
                    if not dest_partner_id:
                        log_entry['Status'] = 'Error'
                        log_entry['Message'] = f"Vendor '{pay['partner_id'][1]}' not found in Odoo 19."
                        migration_logs.append(log_entry)
                        continue

                    dest_journal_id = journal_map[src_j_id]
                    
                    vals = {
                        'payment_type': 'outbound', 'partner_type': 'supplier', 'partner_id': dest_partner_id,
                        'amount': pay['amount'], 'date': pay['date'], 'name': pay_name,
                        'journal_id': dest_journal_id, 'company_id': dest_company_id, 'memo': memo
                    }
                    
                    new_pay_id = dest_client.execute_kw('account.payment', 'create', [vals])
                    
                    if pay.get('state') == 'draft':
                        log_entry['Status'] = 'Success'
                        log_entry['Message'] = f"Migrated as Draft to Company ID {dest_company_id}"
                        _logger.info(f"  Successfully migrated {pay_name} (Draft)")
                    else:
                        dest_client.execute_kw('account.payment', 'action_post', [[new_pay_id]])
                        
                        # Force original name after post (Odoo might have re-sequenced it)
                        dest_client.execute_kw('account.payment', 'write', [[new_pay_id], {'name': pay_name, 'state': 'paid'}])
                        # Also force on associated move
                        pay_data = dest_client.execute_kw('account.payment', 'read', [[new_pay_id], ['move_id']])
                        if pay_data and pay_data[0].get('move_id'):
                            move_id = pay_data[0]['move_id'][0]
                            dest_client.execute_kw('account.move', 'write', [[move_id], {'name': pay_name}])
                        
                        reconcile_payment(dest_client, new_pay_id, dest_partner_id, dest_company_id)
                        mark_payment_as_cleared(dest_client, new_pay_id)
                        
                        log_entry['Status'] = 'Success'
                        log_entry['Message'] = f"Migrated to Company ID {dest_company_id}"
                        _logger.info(f"  Successfully migrated {pay_name}")
                        
                except Exception as e:
                    log_entry['Status'] = 'Error'
                    log_entry['Message'] = str(e)
                    _logger.error(f"  Failed {pay_name}: {e}")
                
                migration_logs.append(log_entry)

            offset += args.limit
    except KeyboardInterrupt:
        _logger.info("Migration stopped by user. Saving partial report...")
    finally:
        # 4. Export Report
        if migration_logs:
            report_file = f"vendor_migration_report_{args.company_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            pd.DataFrame(migration_logs).to_excel(report_file, index=False)
            _logger.info(f"Migration report saved to {report_file}")

if __name__ == "__main__":
    main()
