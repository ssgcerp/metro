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
                # print(f"RPC ERROR: {res_json['error']}")
                pass
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
             # raise Exception(result['error']['data']['message'] if 'data' in result['error'] else result['error']['message'])
             return None
        return result.get('result')

def main():
    parser = argparse.ArgumentParser(description='Check Missing Dependencies for Expense Vouchers')
    # Odoo 14 Defaults
    parser.add_argument('--src-url', default='https://erpmfs.com', help='Source Odoo 14 URL')
    parser.add_argument('--src-db', default='metro_production_8_8_22', help='Source Odoo 14 DB')
    parser.add_argument('--src-user', default='Sales.auh@metrofiresystems.com', help='Source Odoo 14 User')
    parser.add_argument('--src-password', default='Sales@185734', help='Source Odoo 14 Password')

    # Odoo 19 Defaults
    parser.add_argument('--dest-url', default='http://localhost:8079', help='Dest Odoo 19 URL')
    parser.add_argument('--dest-db', default='metrodb', help='Dest Odoo 19 DB')
    parser.add_argument('--dest-user', default='admin', help='Dest Odoo 19 User')
    parser.add_argument('--dest-password', default='Amaze@321', help='Dest Odoo 19 Password')
    
    parser.add_argument('--limit', type=int, default=0, help='Limit number of records (0 for all)')

    args = parser.parse_args()

    print("\n" + "="*80)
    print(f"CHECKING MISSING DEPENDENCIES (Journals & Accounts)")
    print("="*80)

    # 1. Connect
    src_client = OdooJsonRpcClient(args.src_url, args.src_db, args.src_user, args.src_password)
    valid_src = src_client.authenticate()

    dest_client = OdooJsonRpcClient(args.dest_url, args.dest_db, args.dest_user, args.dest_password)
    valid_dest = dest_client.authenticate()

    if not valid_src:
        print("CRITICAL: Failed to authenticate with Source Odoo 14.")
        sys.exit(1)
    if not valid_dest:
        print("CRITICAL: Failed to authenticate with Destination Odoo 19.")
        sys.exit(1)

    print("Connected to Source and Destination.")

    # 2. Fetch Source Data
    print("Fetching Source Data...")
    
    # Journals (Header)
    try:
        # We need all journals used in expense vouchers
        # Fetch vouchers
        fields_v14 = ['journal_id', 'expense_line_ids']
        vouchers_v14 = src_client.execute_kw('account.expense.voucher', 'search_read', [[], fields_v14])
        
        if args.limit > 0:
            vouchers_v14 = vouchers_v14[:args.limit]
            
        print(f"Scanning {len(vouchers_v14)} vouchers...")
        
        used_journals = set()
        used_line_ids = []
        
        for v in vouchers_v14:
            if v['journal_id']:
                used_journals.add(v['journal_id'][1])
            if v['expense_line_ids']:
                used_line_ids.extend(v['expense_line_ids'])
        
        # Accounts (Lines)
        # Fetch lines in batches
        used_accounts = {} # Code -> Name
        
        if used_line_ids:
            # Batch size 1000
            for i in range(0, len(used_line_ids), 1000):
                batch_ids = used_line_ids[i:i+1000]
                lines = src_client.execute_kw('account.expense.voucher.line', 'read', [batch_ids, ['account_id']])
                for l in lines:
                    if l['account_id']:
                        # account_id is [ID, "Code Name"] usually
                        # Extract code and name
                        display = l['account_id'][1]
                        parts = display.split(' ', 1)
                        if len(parts) == 2:
                            code = parts[0]
                            name = parts[1]
                        else:
                            code = parts[0]
                            name = ""
                        
                        used_accounts[code] = name
                        
    except Exception as e:
        print(f"Error scanning source: {e}")
        sys.exit(1)

    print(f"\nFound {len(used_journals)} unique Journals used.")
    print(f"Found {len(used_accounts)} unique Accounts used.")

    # 3. Check Destination
    print("\nChecking existence in Destination (Odoo 19)...")
    
    missing_journals = []
    found_journals = 0
    
    for j_name in used_journals:
        res = dest_client.execute_kw('account.journal', 'search_count', [[('name', '=', j_name)]])
        if res > 0:
            found_journals += 1
        else:
            missing_journals.append(j_name)
            
    missing_accounts = [] # List of (code, name)
    found_accounts = 0
    
    for a_code, a_name in used_accounts.items():
        res = dest_client.execute_kw('account.account', 'search_count', [[('code', '=', a_code)]])
        if res > 0:
            found_accounts += 1
        else:
            missing_accounts.append((a_code, a_name))
            
    # 4. Report
    print("\n" + "="*80)
    print("MISSING DEPENDENCIES REPORT")
    print("="*80)
    
    print("\n[MISSING JOURNALS]")
    if missing_journals:
        for m in sorted(missing_journals):
            print(f" - {m}")
    else:
        print(" NONE (All present)")
        
    print("\n[MISSING ACCOUNTS]")
    if missing_accounts:
        for code, name in sorted(missing_accounts, key=lambda x: x[0]):
            print(f" - {code} {name}")
    else:
        print(" NONE (All present)")
        
    print("\n" + "="*80)
    print(f"Summary: Missing {len(missing_journals)} Journals, {len(missing_accounts)} Accounts.")

if __name__ == '__main__':
    main()
