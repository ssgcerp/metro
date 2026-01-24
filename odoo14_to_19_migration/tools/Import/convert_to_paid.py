
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
    parser = argparse.ArgumentParser(description='Convert In Process Payments to Paid')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Odoo 19 URL')
    parser.add_argument('--db', default='metrodb', help='Odoo 19 DB')
    parser.add_argument('--user', default='admin', help='Odoo 19 User')
    parser.add_argument('--password', default='Amaze@321', help='Odoo 19 Password')
    
    args = parser.parse_args()

    print("\n" + "="*80)
    print(f"CONVERTING 'IN PROCESS' PAYMENTS TO 'PAID' (Disable Outstanding)")
    print("="*80)

    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    
    if not client.authenticate():
        print("Authentication failed!")
        sys.exit(1)

    print("Connected to Odoo 19.")

    # 1. Fetch Companies
    start_companies = client.execute_kw('res.company', 'search', [[]])
    ctx = {'allowed_company_ids': start_companies}

    # 2. Search 'in_process' Payments
    domain = [
        ('state', '=', 'in_process'),
        ('partner_type', '=', 'supplier')
    ]
    
    pay_ids = client.execute_kw('account.payment', 'search', [domain], {'context': ctx})
    print(f"Found {len(pay_ids)} payments in 'In Process' state.")
    
    if not pay_ids:
        print("Nothing to do.")
        sys.exit(0)
    
    # 3. Process by Journal to minimize Config updates
    # We read all payments to group by Journal
    # Batch read for speed
    print("Reading payment details...")
    payments_data = []
    chunk_size = 500
    for i in range(0, len(pay_ids), chunk_size):
        chunk = pay_ids[i:i+chunk_size]
        res = client.execute_kw('account.payment', 'read', [chunk, ['journal_id']], {'context': ctx})
        if isinstance(res, list):
            payments_data.extend(res)
        else:
             print(f"Error reading chunk {i}: {res}")
            
    # Group
    journal_map = {} # journal_id -> [pay_ids]
    for p in payments_data:
        if not p.get('journal_id'): continue
        jid = p['journal_id'][0]
        if jid not in journal_map:
            journal_map[jid] = {'name': p['journal_id'][1], 'ids': []}
        journal_map[jid]['ids'].append(p['id'])
        
    print(f"Grouped into {len(journal_map)} Journals.")
    
    # Process Each Journal
    for jid, data in journal_map.items():
        jname = data['name']
        pids = data['ids']
        print(f"\nProcessing Journal '{jname}' (ID {jid}) - {len(pids)} payments...")
        
        # Check Config
        j_config_res = client.execute_kw('account.journal', 'read', [[jid], ['outbound_payment_method_line_ids']], {'context': ctx})
        if not j_config_res or not isinstance(j_config_res, list):
             print(f"  -> Error reading Journal {jname}: {j_config_res}")
             continue
        j_config = j_config_res[0]

        # Check Payment Method Lines (Outbound)
        # We need to find if ANY outbound line has an account set
        pm_line_ids = j_config.get('outbound_payment_method_line_ids', [])
        if not pm_line_ids:
             print(f"  -> Journal has no outbound payment methods. Skipping.")
             continue
             
        # Read lines
        pm_lines = client.execute_kw('account.payment.method.line', 'read', [pm_line_ids, ['name', 'payment_account_id']], {'context': ctx})
        
        has_outstanding = False
        lines_to_clear = []
        for pml in pm_lines:
             if pml.get('payment_account_id'):
                  has_outstanding = True
                  lines_to_clear.append(pml['id'])
                  print(f"  -> Found Outstanding Account on method '{pml['name']}': {pml['payment_account_id']}")

        if has_outstanding:
            print(f"  -> Disabling Outstanding Accounts on {len(lines_to_clear)} lines...")
            
            # 1. RESET Payments to Draft
            print(f"  -> Resetting {len(pids)} payments to Draft...")
            res_draft = client.execute_kw('account.payment', 'action_draft', [pids], {'context': ctx})
            if isinstance(res_draft, dict) and 'error' in res_draft:
                 print(f"  -> FAILED to Reset to Draft: {res_draft['error']}")
                 continue
            
            # 2. UPDATE Method Lines (Clear Account)
            print("  -> Clearing 'payment_account_id' on Method Lines...")
            for pml_id in lines_to_clear:
                client.execute_kw('account.payment.method.line', 'write', [[pml_id], {'payment_account_id': False}], {'context': ctx})
            
            # 3. REPOST Payments
            print(f"  -> Reposting {len(pids)} payments...")
            res_post = client.execute_kw('account.payment', 'action_post', [pids], {'context': ctx})
            if isinstance(res_post, dict) and 'error' in res_post:
                 print(f"  -> FAILED to Repost: {res_post['error']}")
                 continue
                 
            # 4. VERIFY State
            posted_count = client.execute_kw('account.payment', 'search_count', [[('id', 'in', pids), ('state', '=', 'posted')]], {'context': ctx})
            print(f"  -> Success: {posted_count}/{len(pids)} are now 'Posted' (Paid in Bill terms).")
            
        else:
            print("  -> Journal ALREADY has no Outstanding Accounts on Method Lines. Payments should be Paid? Checking...")
            # If 'in_process', it means they were posted when it WAS set.
            # We must Reset and Repost.
            print(f"  -> Resetting & Reposting {len(pids)} payments to apply current config...")
            client.execute_kw('account.payment', 'action_draft', [pids], {'context': ctx})
            client.execute_kw('account.payment', 'action_post', [pids], {'context': ctx})
            print("  -> Done.")
            print("  -> Journal ALREADY has no Outstanding Account. Payments should be Paid? Checking...")
            # If they are 'in_process' but journal has no account, maybe they were posted when it WAS set?
            # We must Reset and Repost to update them.
            print(f"  -> Resetting & Reposting {len(pids)} payments to apply current config...")
            client.execute_kw('account.payment', 'action_draft', [pids], {'context': ctx})
            client.execute_kw('account.payment', 'action_post', [pids], {'context': ctx})
            print("  -> Done.")

    print("\nDone.")

if __name__ == "__main__":
    main()
