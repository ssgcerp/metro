
import json
import random
import sys
import time
import requests
import argparse
import logging
import re

# Configure logging
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
                return res_json
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
             return result
        if hasattr(result, 'get_result'):
             return result.get_result()
        return result.get('result')

def main():
    parser = argparse.ArgumentParser(description='Fix Payment Status (Paid) and Reconcile')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Odoo 19 URL')
    parser.add_argument('--db', default='metrodb', help='Odoo 19 DB')
    parser.add_argument('--user', default='admin', help='Odoo 19 User')
    parser.add_argument('--password', default='Amaze@321', help='Odoo 19 Password')
    
    args = parser.parse_args()

    print("\n" + "="*80)
    print(f"FIX PAYMENT STATUS AND RECONCILE (Steps 1 & 2)")
    print("="*80)

    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    if not client.authenticate():
        print("Authentication failed!")
        sys.exit(1)
    print("Connected to Odoo 19.")
    
    # Context with all companies
    start_companies = client.execute_kw('res.company', 'search', [[]])
    ctx = {'allowed_company_ids': start_companies}
    
    # STEP 1: CONVERT 'IN PROCESS' TO 'PAID' (Reset -> Config -> Repost)
    print("\n" + "-"*60)
    print("STEP 1: Checking for 'In Process' Payments...")
    print("-"*60)
    
    domain_inp = [('state', '=', 'in_process'), ('partner_type', '=', 'supplier')]
    pay_ids_inp = client.execute_kw('account.payment', 'search', [domain_inp], {'context': ctx})
    if pay_ids_inp:
        print(f"Found {len(pay_ids_inp)} 'In Process' payments. Fixing status...")
        # Better strategy: Group by Payment Method Line ID (PML)
        # Because we need to fix the specific line used by the payment.
        pml_map = {} # pml_id -> [pay_ids]
        
        # Read Method Line from Payments
        # We need 'payment_method_line_id' from earlier search?
        # Re-read
        print(f"Reading {len(pay_ids_inp)} payments for Method Line info...")
        chunk_size = 1000
        pay_data_pml = []
        for i in range(0, len(pay_ids_inp), chunk_size):
             chunk = pay_ids_inp[i:i+chunk_size]
             res = client.execute_kw('account.payment', 'read', [chunk, ['payment_method_line_id', 'journal_id']], {'context': ctx})
             if isinstance(res, list): pay_data_pml.extend(res)
             
        for p in pay_data_pml:
            if not p.get('payment_method_line_id'): continue
            pml_id = p['payment_method_line_id'][0]
            if pml_id not in pml_map:
                j_info = p.get('journal_id', [0,'Unknown'])
                pml_map[pml_id] = {'name': p['payment_method_line_id'][1], 'ids': [], 'journal': j_info[1], 'journal_id_int': j_info[0]}
            pml_map[pml_id]['ids'].append(p['id'])
            
        print(f"Grouped into {len(pml_map)} Payment Method Lines.")
        
        for pml_id, data in pml_map.items():
             pids = data['ids']
             # Check Config of this Line
             pml_data = client.execute_kw('account.payment.method.line', 'read', [[pml_id], ['payment_account_id', 'name']], {'context': ctx})[0]
             
             if pml_data.get('payment_account_id'):
                 # Check if it is the Bank Account?
                 # If it is Bank Account, we don't need to disable/repost necessarily, but maybe we do to trigger update?
                 # Actually, let's just proceed to Force Write.
                 # But if it is an OLD outstanding account, we should clear it.
                 # How to know? Compare with Bank ID?
                 # Let's clean it anyway (Reset/Clear/Post), THEN Force Write.
                  print(f"  -> Found Configured Account {pml_data['payment_account_id']} on Method '{data['name']}'. Resetting/Clearing to ensure clean state...")
                  client.execute_kw('account.payment', 'action_draft', [pids], {'context': ctx})
                  client.execute_kw('account.payment.method.line', 'write', [[pml_id], {'payment_account_id': False}], {'context': ctx})
                  client.execute_kw('account.payment', 'action_post', [pids], {'context': ctx})
             else:
                  print(f"  -> Method '{data['name']}' has NO account. Ensuring Repost...")
                  client.execute_kw('account.payment', 'action_draft', [pids], {'context': ctx})
                  client.execute_kw('account.payment', 'action_post', [pids], {'context': ctx})

             # NOW: STRATEGY C - Force Write Outstanding Account (ALWAYS)
             print(f"  -> STRATEGY C: Force Writing 'outstanding_account_id' to Journal Bank Account.")
             target_jid = data['journal_id_int']
             if target_jid:
                 j_def = client.execute_kw('account.journal', 'read', [[target_jid], ['default_account_id']], {'context': ctx})[0]
                 bank_acc_id = j_def.get('default_account_id')
                 if bank_acc_id: bank_acc_id = bank_acc_id[0]
                 
                 if bank_acc_id:
                      print(f"     Journal Default Account: {bank_acc_id}. Updating {len(pids)} payments...")
                      try:
                          client.execute_kw('account.payment', 'write', [pids, {'outstanding_account_id': bank_acc_id}], {'context': ctx})
                          print("     Write Executed.")
                      except Exception as e:
                          print(f"     Write Failed: {e}")
                 else:
                      print("     Failed: Journal has no Default Bank/Cash Account!")
        print("No 'In Process' payments found. (Step 1 Completed)")

    # STEP 2: RECONCILE LINKED BILLS
    print("\n" + "-"*60)
    print("STEP 2: Reconciling Payments to Bills...")
    print("-"*60)
    
    # Domain: Posted OR In Process (since we fixed account, they act as paid)
    # AND Unreconciled
    domain_posted = [('state', 'in', ['posted', 'in_process']), ('partner_type', '=', 'supplier'), ('is_reconciled', '=', False)]
    pay_ids_posted = client.execute_kw('account.payment', 'search', [domain_posted], {'context': ctx})
    
    print(f"Found {len(pay_ids_posted)} Posted but Unreconciled payments.")
    
    reconciled_count = 0
    failed_link_count = 0
    
    # Process individually for reconciliation logic
    for i, pay_id in enumerate(pay_ids_posted):
        # Progress every 50
        if i % 50 == 0: print(f"Processing... {i}/{len(pay_ids_posted)}")
            
        try:
            # Read Info
            pay_data = client.execute_kw('account.payment', 'read', [[pay_id], ['name', 'memo', 'move_id']], {'context': ctx})[0]
            ref = pay_data.get('memo')
            name = pay_data.get('name')
            
            if not ref:
                 continue
                 
            clean_ref = str(ref).replace("Bill: ", "").strip()
            
            # Find Bill
            bill_domain = [
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', '!=', 'paid'),
                '|', ('name', '=', clean_ref), ('ref', '=', clean_ref)
            ]
            
            bills = client.execute_kw('account.move', 'search_read', [bill_domain], {'fields': ['id', 'name'], 'limit': 1, 'context': ctx})
            
            if bills:
                bill_id = bills[0]['id']
                pay_move_id = pay_data['move_id'][0]
                
                p_lines = client.execute_kw('account.move.line', 'search', [
                    [('move_id', '=', pay_move_id), ('account_id.account_type', '=', 'liability_payable'), ('reconciled', '=', False)]
                ], {'context': ctx})
                
                b_lines = client.execute_kw('account.move.line', 'search', [
                    [('move_id', '=', bill_id), ('account_id.account_type', '=', 'liability_payable'), ('reconciled', '=', False)]
                ], {'context': ctx})
                
                if p_lines and b_lines:
                    client.execute_kw('account.move.line', 'reconcile', [p_lines + b_lines], {'context': ctx})
                    reconciled_count += 1
                    # print(f"  -> Reconciled Payment {name} with Bill {bills[0]['name']}")
                else:
                    # print(f"  -> Match found but lines already reconciled? {name}")
                    pass
            else:
                failed_link_count += 1
                
        except Exception as e:
            # print(f"Error Reconciling {pay_id}: {e}")
            pass
            
    print(f"Reconciliation Complete. Reconciled: {reconciled_count}. No Link Found: {failed_link_count}")

if __name__ == "__main__":
    main()
