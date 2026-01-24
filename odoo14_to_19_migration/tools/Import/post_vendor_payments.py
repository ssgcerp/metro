
import json
import random
import sys
import time
import requests
import argparse
import logging

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
    parser = argparse.ArgumentParser(description='Post Vendor Payments and Reconcile')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Odoo 19 URL')
    parser.add_argument('--db', default='metrodb', help='Odoo 19 DB')
    parser.add_argument('--user', default='admin', help='Odoo 19 User')
    parser.add_argument('--password', default='Amaze@321', help='Odoo 19 Password')
    
    args = parser.parse_args()

    print("\n" + "="*80)
    print(f"POSTING & RECONCILING VENDOR PAYMENTS")
    print("="*80)

    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    
    if not client.authenticate():
        print("Authentication failed!")
        sys.exit(1)

    print("Connected to Odoo 19.")

    # 1. Search Draft Vendor Payments
    # partner_type='supplier', state='draft'
    domain = [
        ('partner_type', '=', 'supplier'),
        ('state', '=', 'draft')
    ]
    
    # We also need to be able to access all companies
    # But search usually respects allowed_company_ids in context.
    # We should fetch all companies and allow them.
    companies = client.execute_kw('res.company', 'search', [[]])
    ctx = {'allowed_company_ids': companies}
    
    payment_ids = client.execute_kw('account.payment', 'search', [domain], {'context': ctx})
    
    if not payment_ids:
        print("No Draft Vendor Payments found.")
        sys.exit(0)
        
    print(f"Found {len(payment_ids)} draft payments. Processing...")
    
    success_count = 0
    reconcile_count = 0
    fail_count = 0
    
    for i, pay_id in enumerate(payment_ids):
        try:
            # Read Info
            read_res = client.execute_kw('account.payment', 'read', [[pay_id], ['name', 'memo', 'amount', 'partner_id', 'move_id']], {'context': ctx})
            if not read_res or isinstance(read_res, dict): # Dict means error (from my wrapper)
                err_msg = str(read_res)
                if isinstance(read_res, dict) and 'error' in read_res:
                     err_msg = read_res['error']['data'].get('message', read_res['error'])
                print(f"[{i+1}/{len(payment_ids)}] ID {pay_id}: READ FAILED. Reason: {err_msg}")
                fail_count += 1
                continue
                
            pay_data = read_res[0]
            name = pay_data.get('name')
            ref = pay_data.get('memo') # Use Memo as Ref
            # Extract ref if it's formatted like "Bill: REF" (though import script used clean ref)
            if ref:
                # remove "Bill: " prefix if present (from my import script debugging if any)
                clean_ref = str(ref).replace("Bill: ", "").strip()
            else:
                clean_ref = name # Fallback
                
            print(f"[{i+1}/{len(payment_ids)}] Payment {name} (Ref: {ref})...", end=" ")

            # POST
            try:
                res_post = client.execute_kw('account.payment', 'action_post', [[pay_id]], {'context': ctx})
                # Check status
                check = client.execute_kw('account.payment', 'read', [[pay_id], ['state']], {'context': ctx})
                if check and check[0]['state'] in ['posted', 'in_process']:
                    print("POSTED.", end=" ")
                    success_count += 1
                else:
                    err = str(res_post)
                    if isinstance(res_post, dict) and 'error' in res_post:
                        err = res_post['error']['data'].get('message', res_post['error'])
                        
                        # HEALING: Missing Account
                        if "Missing required account" in err:
                             print("     [Fixing] Missing Account Error detected. Checking BOTH Partner and Journal accounts...")
                             
                             # 1. FIX DESTINATION ACCOUNT (Partner)
                             p_check = client.execute_kw('account.payment', 'read', [[pay_id], ['destination_account_id', 'company_id', 'journal_id']], {'context': ctx})[0]
                             comp_id = p_check['company_id'][0]
                             
                             if not p_check.get('destination_account_id'):
                                 accs = client.execute_kw('account.account', 'search', [[('account_type', '=', 'liability_payable'), ('company_ids', 'in', [comp_id])]], {'limit': 1, 'context': ctx})
                                 if accs:
                                     print(f"     [Fix 1/2] Setting destination_account_id to {accs[0]}")
                                     client.execute_kw('account.payment', 'write', [[pay_id], {'destination_account_id': accs[0]}], {'context': ctx})
                                 else:
                                     print("     [Fix 1/2 Failed] No Payable account found in company.")
                             
                             # 2. FIX JOURNAL ACCOUNT (Outstanding)
                             # p_check has 'journal_id'
                             if not p_check.get('journal_id'):
                                 print("     [Fix 2/2 Failed] Payment has no Journal set!")
                                 continue
                                 
                             j_id = p_check['journal_id'][0] # Check done above
                             
                             j_data_res = client.execute_kw('account.journal', 'read', [[j_id], ['payment_credit_account_id']], {'context': ctx})
                             if not j_data_res or not isinstance(j_data_res, list):
                                  print(f"     [Fix 2/2 Failed] Could not read Journal {j_id}")
                                  continue
                                  
                             j_data = j_data_res[0]
                             
                             if not j_data.get('payment_credit_account_id'):
                                  # Find "Outstanding Payments" or "Bank" account
                                  out_accs = client.execute_kw('account.account', 'search', [[('name', 'ilike', 'Outstanding Payment'), ('company_ids', 'in', [comp_id])]], {'limit': 1, 'context': ctx})
                                  if not out_accs:
                                      out_accs = client.execute_kw('account.account', 'search', [[('name', 'ilike', 'Bank'), ('company_ids', 'in', [comp_id])]], {'limit': 1, 'context': ctx})
                                  
                                  if out_accs:
                                       print(f"     [Fix 2/2] Setting Journal '{p_check['journal_id'][1]}' Credit Account to {out_accs[0]}")
                                       client.execute_kw('account.journal', 'write', [[j_id], {'payment_credit_account_id': out_accs[0]}], {'context': ctx})
                                  else:
                                       print("     [Fix 2/2 Failed] No suitable Outstanding/Bank account found.")
                             
                             # 3. RETRY POST (Once)
                             print("     [Retry] Posting after fixes...")
                             res_post_2 = client.execute_kw('account.payment', 'action_post', [[pay_id]], {'context': ctx})
                             
                             check2 = client.execute_kw('account.payment', 'read', [[pay_id], ['state']], {'context': ctx})
                             if check2 and check2[0]['state'] in ['posted', 'in_process']:
                                 print("POSTED (After Fixes).", end=" ")
                                 success_count += 1
                                 pass # Proceed to reconcile
                             else:
                                 # Get fresh error if any
                                 err2 = str(res_post_2)
                                 if isinstance(res_post_2, dict) and 'error' in res_post_2:
                                      err2 = res_post_2['error']['data'].get('message', res_post_2['error'])
                                 print(f"FAILED (Even after Fixes: {err2})")
                                 fail_count += 1
                                 continue
                        else:
                             print(f"FAILED (State: {check[0]['state']}, Result: {err})")
                             fail_count += 1
                             continue

                    else:
                        print(f"FAILED (State: {check[0]['state']}, Result: {err})")
                        fail_count += 1
                        continue
            except Exception as e:
                print(f"POST ERROR: {e}")
                fail_count += 1
                continue
                
            # RECONCILE
            # Strategy: Find Bill with 'clean_ref'
            if not clean_ref:
                print("(No Link Info)")
                continue

            bill_domain = [
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', '!=', 'paid'), # Only unpaid
                '|', ('name', '=', clean_ref), ('ref', '=', clean_ref)
            ]
            
            bills = client.execute_kw('account.move', 'search_read', [bill_domain], {'fields': ['id', 'name'], 'limit': 1, 'context': ctx})
            
            if bills:
                item = bills[0]
                bill_id = item['id']
                bill_name = item['name']
                
                # Reconcile Logic
                # 1. Get Payment Move Lines (Payable)
                # Need move_id. Payment read usually includes it.
                # Refresh payment read to be sure
                pay_data = client.execute_kw('account.payment', 'read', [[pay_id], ['move_id']], {'context': ctx})[0]
                pay_move_id = pay_data['move_id'][0]
                
                # Search Payable Lines
                # Account type 'liability_payable' (or 'payable')
                # Odoo 19: account_type selection.
                
                # Payment Lines
                p_lines = client.execute_kw('account.move.line', 'search', [
                    [('move_id', '=', pay_move_id), ('account_id.account_type', '=', 'liability_payable'), ('reconciled', '=', False)]
                ], {'context': ctx})
                
                # Bill Lines
                b_lines = client.execute_kw('account.move.line', 'search', [
                    [('move_id', '=', bill_id), ('account_id.account_type', '=', 'liability_payable'), ('reconciled', '=', False)]
                ], {'context': ctx})
                
                if p_lines and b_lines:
                    lines_to_rec = p_lines + b_lines
                    try:
                        client.execute_kw('account.move.line', 'reconcile', [lines_to_rec], {'context': ctx})
                        print(f"RECONCILED with Bill {bill_name}.")
                        reconcile_count += 1
                    except Exception as re:
                         print(f"RECONCILE ERROR: {re}")
                else:
                    print(f"No reconcileable lines found (Bill: {bill_name}).")
            else:
                print(f"Linked Bill '{clean_ref}' not found or already paid.")

        except Exception as e:
            print(f"EXCEPTION: {e}")
            fail_count += 1
            
    print("\n" + "="*80)
    print(f"DONE. Posted: {success_count}, Reconciled: {reconcile_count}, Failed: {fail_count}")
    print("="*80)

if __name__ == "__main__":
    main()
