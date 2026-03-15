import pandas as pd
import argparse
import logging
import time
import requests
import random
import os
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
_logger = logging.getLogger(__name__)

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
                print(f"RPC ERROR: {res_json['error']}")
            return res_json
        except Exception as e:
            print(f"RPC EXCEPTION: {e}")
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

        pay_lines = client.execute_kw('account.move.line', 'search_read', 
            [[('move_id', '=', move_id), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]],
            {'fields': ['id', 'credit']}
        )
        if not pay_lines: return
        payment_line_id = pay_lines[0]['id']
        payment_amount = pay_lines[0]['credit']

        matched_line_id = False
        memo = payment[0].get('memo')
        
        if memo:
            invs = client.execute_kw('account.move', 'search_read', 
                [[('name', '=', memo), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('payment_state', '!=', 'paid'), ('company_id', '=', dest_company_id)]], 
                {'fields': ['id']}
            )
            if invs:
                inv_lines = client.execute_kw('account.move.line', 'search_read', 
                    [[('move_id', '=', invs[0]['id']), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]],
                    {'fields': ['id']}
                )
                if inv_lines: matched_line_id = inv_lines[0]['id']

        if not matched_line_id and partner_id:
            open_lines = client.execute_kw('account.move.line', 'search_read', 
                [[('parent_state', '=', 'posted'), ('account_id.account_type', '=', 'asset_receivable'), ('partner_id', '=', partner_id), ('reconciled', '=', False), ('move_id.move_type', '=', 'out_invoice'), ('company_id', '=', dest_company_id), ('debit', '>', 0)]], 
                {'fields': ['id', 'debit']}
            )
            if open_lines:
                for line in open_lines:
                    if abs(line['debit'] - payment_amount) < 0.01:
                        matched_line_id = line['id']
                        break
        
        if matched_line_id:
             try:
                 client.execute_kw('account.move.line', 'reconcile', [[payment_line_id, matched_line_id]])
                 _logger.info(f"  Reconciled properly")
             except Exception as e:
                 if "marshal None" in str(e):
                     _logger.info(f"  Reconciled properly")
                 else:
                     _logger.warning(f"  Failed reconcile: {e}")
    except Exception as e:
        _logger.error(f"  Reconciliation check failed: {e}")

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

        clearance_move_vals = {
            'journal_id': journal_id,
            'date': payment_date,
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {
                    'account_id': bank_account_id,
                    'name': f"Bank Clearance - {payment_name}",
                    'debit': amount,
                    'credit': 0.0,
                    'currency_id': currency_id,
                }),
                (0, 0, {
                    'account_id': outstanding_account_id,
                    'name': f"Clearance - {payment_name}",
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
        _logger.warning(f"  Failed to mark as Paid: {e}")


def main():
    parser = argparse.ArgumentParser(description='Migrate Odoo 19 Customer Payments via Excel Map')
    parser.add_argument('--src-db', default='metrodb', help='Source DB')
    parser.add_argument('--dest-db', default='newdb', help='Destination DB')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Odoo URL')
    parser.add_argument('--user', default='admin', help='Admin User')
    parser.add_argument('--password', default='Amaze@321', help='Admin Password')
    
    parser.add_argument('--company-name', required=True, help='Exact name of the Source Company to migrate')
    parser.add_argument('--excel-map', required=True, help='Path to Excel mapping file')
    parser.add_argument('--limit', type=int, default=100, help='Batch size')

    args = parser.parse_args()

    if not os.path.exists(args.excel_map):
        print(f"ERROR: Excel mapping file '{args.excel_map}' not found.")
        return

    try:
        df = pd.read_excel(args.excel_map)
        
        journal_map = {}
        for index, row in df.iterrows():
            if str(row['Source Company']) == args.company_name:
                src_j_id = int(row['Source Journal ID'])
                dest_j_id = row['Dest Journal ID']
                dest_c_name = row['Dest Company']
                dest_p_name = row.get('Parent Company', '')
                
                if pd.isna(dest_j_id) or pd.isna(dest_c_name):
                    print(f"WARNING: Skipping mapping for Journal '{row.get('Source Journal Name', '')}' because Dest Journal ID or Dest Company is missing.")
                    continue
                    
                journal_map[src_j_id] = {
                    'dest_journal_id': int(dest_j_id),
                    'dest_company_name': str(dest_c_name),
                    'parent_company_name': str(dest_p_name) if not pd.isna(dest_p_name) else ''
                }
                
        if not journal_map:
             print(f"ERROR: No valid mappings found in Excel for Source Company '{args.company_name}'.")
             return
             
    except Exception as e:
        print(f"Failed to load Excel map: {e}")
        return

    src_client = OdooJsonRpcClient(args.url, args.src_db, args.user, args.password)
    dest_client = OdooJsonRpcClient(args.url, args.dest_db, args.user, args.password)
    
    if not src_client.authenticate() or not dest_client.authenticate():
        print("Authentication failed.")
        return

    src_company_search = src_client.execute_kw('res.company', 'search', [[('name', '=', args.company_name)]], {'limit': 1})
    if not src_company_search:
        print(f"ERROR: Source Company '{args.company_name}' not found in {args.src_db}.")
        return
    src_company_id = src_company_search[0]

    dest_companies = {} 
    
    # Check parent and branch companies
    for src_j_id, mapping in journal_map.items():
        c_name = mapping['dest_company_name']
        p_name = mapping['parent_company_name']
        
        lookup_key = f"{c_name}_{p_name}"
        if lookup_key not in dest_companies:
            domain = [('name', '=', c_name)]
            
            # If a parent company name is provided, ensure we match exactly the branch belonging to that parent
            if p_name:
                parent_search = dest_client.execute_kw('res.company', 'search', [[('name', '=', p_name)]], {'limit': 1})
                if parent_search:
                    domain.append(('parent_id', '=', parent_search[0]))
                else:
                    print(f"WARNING: Parent Company '{p_name}' not found in target DB! Proceeding without parent constraint.")

            search_c = dest_client.execute_kw('res.company', 'search', [domain], {'limit': 1})
            if search_c:
                dest_companies[lookup_key] = search_c[0]
            else:
                 print(f"WARNING: Dest Company '{c_name}' not found in {args.dest_db} (under parent {p_name}). Related journals will fail.")
                 dest_companies[lookup_key] = False

    offset = 0
    domain = [
        ('payment_type', '=', 'inbound'),
        ('partner_type', '=', 'customer'),
        ('state', 'in', ['paid', 'in_process', 'draft', 'posted']),
        ('company_id', '=', src_company_id)
    ]

    print(f"Pre-fetching existing payments from destination for {len(dest_companies)} target companies...")
    all_existing_names = set()
    for lookup_key, d_comp_id in dest_companies.items():
        if not d_comp_id: continue
        d_offset = 0
        while True:
            batch = dest_client.execute_kw('account.payment', 'search_read', 
                [[('company_id', '=', d_comp_id)]], 
                {'fields': ['name'], 'limit': 1000, 'offset': d_offset})
            if not batch: break
            for b in batch:
                all_existing_names.add(b['name'])
            d_offset += 1000
    
    print(f"Found {len(all_existing_names)} existing payments in destination.")
    
    print(f"\nStarting migration for Source Company '{args.company_name}'...")
    
    while True:
        payments = src_client.execute_kw('account.payment', 'search_read', [domain], 
            {'fields': ['name', 'date', 'amount', 'partner_id', 'journal_id', 'currency_id', 'memo', 'state'], 
             'limit': args.limit, 'offset': offset, 'order': 'date asc'})
        
        if not payments:
            break

        for pay in payments:
            pay_name = pay['name']
            src_j_id = pay['journal_id'][0]
            
            if src_j_id not in journal_map:
                continue
                
            mapping = journal_map[src_j_id]
            dest_journal_id = mapping['dest_journal_id']
            dest_c_name = mapping['dest_company_name']
            dest_p_name = mapping['parent_company_name']
            
            lookup_key = f"{dest_c_name}_{dest_p_name}"
            dest_company_id = dest_companies.get(lookup_key)
            
            if not dest_company_id:
                print(f"  Skipping {pay_name}: Dest Company '{dest_c_name}' could not be resolved.")
                continue

            if pay_name in all_existing_names:
                # Still check search_count just in case of concurrent runs, but skip the set match first
                continue
            
            # Check for duplicate (Final safety check)
            if dest_client.execute_kw('account.payment', 'search_count', [[('name', '=', pay_name), ('company_id', '=', dest_company_id)]]) > 0:
                print(f"  Skipping {pay_name} - Already exists in dest company {dest_c_name} (Confirmed via RPC).")
                all_existing_names.add(pay_name) # Add to set to skip faster next time
                continue

            # Map Partner
            src_partner_name = pay['partner_id'][1] if pay['partner_id'] else ''
            dest_partner_search = dest_client.execute_kw('res.partner', 'search', [[('name', '=', src_partner_name)]], {'limit': 1})
            if not dest_partner_search:
                print(f"  Skipping {pay_name}: Partner '{src_partner_name}' not found in destination.")
                continue
            dest_partner_id = dest_partner_search[0]

            vals = {
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': dest_partner_id,
                'amount': pay['amount'],
                'date': pay['date'],
                'name': pay_name,
                'journal_id': dest_journal_id,
                'company_id': dest_company_id,
                'memo': pay.get('memo', '')
            }

            try:
                # Create the Payment
                new_payment_id = dest_client.execute_kw('account.payment', 'create', [vals])
                print(f"  Created Payment: {pay_name} (ID: {new_payment_id}) in {dest_c_name}")
                
                # Only post and reconcile if the source payment was NOT in draft state
                if pay['state'] != 'draft':
                    # Post the payment directly
                    res_post = dest_client.execute_kw('account.payment', 'action_post', [[new_payment_id]])
                     
                    # Automatically reconcile against open invoices based on Memo or exact amount
                    reconcile_payment(dest_client, new_payment_id, dest_partner_id, dest_company_id)
                    
                    # Automatically mark payment as fully cleared with the bank
                    mark_payment_as_cleared(dest_client, new_payment_id)
                else:
                    print(f"  -> Left as DRAFT (source state was draft)")
                
            except Exception as e:
                print(f"  Failed to create {pay_name}: {e}")

        offset += args.limit
        time.sleep(0.5)

    print("\nMigration for company finished.")

if __name__ == "__main__":
    main()
