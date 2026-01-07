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
                print(f"RPC ERROR: {res_json['error']}")
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
             print(f"RPC ERROR in {method}: {result['error']}")
             return None
        return result.get('result')

def map_account_type(v14_type_rec):
    """
    Maps Odoo 14 account.account.type to Odoo 19 account_type selection.
    v14_type_rec is a dictionary containing 'type' (e.g. receivable) and 'internal_group' (e.g. Asset).
    """
    if not v14_type_rec:
        return 'expense' # Fallback
        
    t_type = v14_type_rec.get('type')
    t_group = v14_type_rec.get('internal_group') # equity, asset, liability, income, expense
    
    # Standard mapping logic
    if t_type == 'receivable': return 'asset_receivable'
    if t_type == 'payable': return 'liability_payable'
    if t_type == 'liquidity': return 'asset_cash'
    
    if t_group == 'income': return 'income'
    if t_group == 'expense': return 'expense'
    if t_group == 'equity': return 'equity'
    
    if t_group == 'asset':
        if t_type == 'current': return 'asset_current'
        return 'asset_non_current'
        
    if t_group == 'liability':
        if t_type == 'current': return 'liability_current'
        return 'liability_non_current'
        
    return 'expense' # Default fallback

def main():
    parser = argparse.ArgumentParser(description='Create Missing CoA in Odoo 19')
    # Odoo 14 Defaults
    parser.add_argument('--src-url', default='https://erpmfs.com', help='Source Odoo 14 URL')
    parser.add_argument('--src-db', default='metro_production_8_8_22', help='Source Odoo 14 DB')
    parser.add_argument('--src-user', default='Sales.auh@metrofiresystems.com', help='Source Odoo 14 User')
    parser.add_argument('--src-password', default='Sales@185734', help='Source Odoo 14 Password')

    # Odoo 19 Defaults
    parser.add_argument('--dest-url', default='http://localhost:8079', help='Dest Odoo 19 URL')
    parser.add_argument('--dest-db', default='metrodb', help='Dest Odoo 19 User')
    parser.add_argument('--dest-user', default='admin', help='Dest Odoo 19 User')
    parser.add_argument('--dest-password', default='Amaze@321', help='Dest Odoo 19 Password')
    
    # Missing codes list passed as argument or we can just fetch all used in expenses again to be safe
    # User said "create missing CoA", implying based on the report.
    # We will re-run the scanning logic to identify them dynamically.

    args = parser.parse_args()

    print("\n" + "="*80)
    print(f"CREATING MISSING ACCOUNTS")
    print("="*80)

    # 1. Connect
    src_client = OdooJsonRpcClient(args.src_url, args.src_db, args.src_user, args.src_password)
    if not src_client.authenticate():
        print("Failed to authenticate with Source Odoo 14")
        sys.exit(1)

    dest_client = OdooJsonRpcClient(args.dest_url, args.dest_db, args.dest_user, args.dest_password)
    if not dest_client.authenticate():
        print("Failed to authenticate with Destination Odoo 19")
        sys.exit(1)

    print("Connected.")

    # 2. Fetch Dest Companies
    companies = dest_client.execute_kw('res.company', 'search_read', [[], ['id', 'name']])
    all_company_ids = [c['id'] for c in companies]
    print(f"Found {len(companies)} companies in Odoo 19.")
    
    if not all_company_ids:
        print("No companies found!")
        sys.exit(1)

    # 3. Identify Missing Accounts (Scan Expense Vouchers again)
    print("Scanning Source Expense Vouchers for used accounts...")
    
    used_accounts_codes = set()
    
    # Fetch all vouchers to be thorough
    fields_v14 = ['expense_line_ids']
    vouchers = src_client.execute_kw('account.expense.voucher', 'search_read', [[], fields_v14])
    
    all_line_ids = []
    for v in vouchers:
        if v['expense_line_ids']:
            all_line_ids.extend(v['expense_line_ids'])
            
    # Batch Read Lines
    print(f"Scanning {len(all_line_ids)} lines...")
    
    for i in range(0, len(all_line_ids), 1000):
        batch = all_line_ids[i:i+1000]
        # Read account_id from lines
        lines_data = src_client.execute_kw('account.expense.voucher.line', 'read', [batch, ['account_id']])
        for l in lines_data:
            if l['account_id']:
                # [ID, "Code Name"]
                display = l['account_id'][1]
                code = display.split(' ')[0]
                used_accounts_codes.add(code)
                
    print(f"Identified {len(used_accounts_codes)} unique accounts used in Source Expenses.")

    # 4. Filter for Missing in Dest
    missing_codes = []
    for code in used_accounts_codes:
        # Check by Code
        exists = dest_client.execute_kw('account.account', 'search_count', [[('code', '=', code)]])
        if exists == 0:
            missing_codes.append(code)
            
    print(f"Found {len(missing_codes)} accounts MISSING in Odoo 19.")
    
    if not missing_codes:
        print("All accounts exist. Exiting.")
        return

    # 5. Fetch Details from Source for Missing Codes
    print("Fetching details for missing accounts from Source...")
    # We need to search account.account in Source using these codes
    # Chunking search to avoid giant domains?
    
    src_accounts = []
    for i in range(0, len(missing_codes), 100):
        chunk = missing_codes[i:i+100]
        # Fetch name, code, user_type_id
        # Proper explicit kwargs for fields
        accs = src_client.execute_kw('account.account', 'search_read', 
            [[('code', 'in', chunk)]], 
            {'fields': ['code', 'name', 'user_type_id', 'reconcile']} 
        )
        if accs:
            src_accounts.extend(accs)
        else:
            print(f"Warning: Failed to fetch chunk starting with {chunk[0] if chunk else '?'}")
        
    print(f"Fetched details for {len(src_accounts)} accounts.")
    
    # Cache account types
    # v14 user_type_id is [ID, Name]. We need to read the type record to map it correctly.
    type_ids = set()
    for acc in src_accounts:
        if acc['user_type_id']:
            type_ids.add(acc['user_type_id'][0])
            
    type_map = {} # ID -> {type, internal_group}
    if type_ids:
        types = src_client.execute_kw('account.account.type', 'read', [list(type_ids), ['type', 'internal_group']])
        for t in types:
            type_map[t['id']] = t
            
    # 6. Create in Dest
    created_count = 0
    failed_count = 0
    
    for acc in src_accounts:
        code = acc['code']
        name = acc['name']
        v14_type_id = acc['user_type_id'][0] if acc['user_type_id'] else None
        
        # Map Type
        v14_type_rec = type_map.get(v14_type_id)
        v19_type = map_account_type(v14_type_rec)
        
        print(f"Creating {code} - {name} ({v19_type})...")
        
        # STRATEGY: Create for MAIN company first, then add others one by one.
        main_company_id = all_company_ids[0]
        other_company_ids = all_company_ids[1:]
        
        vals = {
            'code': code,
            'name': name,
            'account_type': v19_type,
            'company_ids': [(6, 0, [main_company_id])], # Start with just one
        }
        
        # Create for Main Company
        ctx = {'allowed_company_ids': [main_company_id]}
        create_res = dest_client.execute_kw('account.account', 'create', [vals], {'context': ctx})
        
        if create_res:
            acc_id = create_res
            # Now add other companies one by one
            for other_id in other_company_ids:
                # We must set the code for this company simultaneously with adding it?
                # Or just setting the code (property) will work? 
                # The constraint checks "company to which this account belongs".
                # If we use write({'company_ids': [(4, other_id)], 'code': code}) in other_id context, it should work.
                
                write_vals = {
                    'company_ids': [(4, other_id)],
                    'code': code
                }
                # Fix AccessError: Must include main_company_id to see the record, 
                # but put other_id first to set env.company for the 'code' write.
                write_ctx = {'allowed_company_ids': [other_id, main_company_id]} 
                
                try:
                    dest_client.execute_kw('account.account', 'write', [[acc_id], write_vals], {'context': write_ctx})
                    # print(f"    Added company {other_id}")
                except Exception as e:
                    print(f"    Failed to add company {other_id}: {e}")
            
            print(f"  Success: Created ID {acc_id} and linked to {len(all_company_ids)} companies.")
            created_count += 1
        else:
            print("  FAILED to create (Unknown reason)")
            failed_count += 1
            
    print("\n" + "="*80)
    print(f"Creation Complete.")
    print(f"Created: {created_count}")
    print(f"Failed : {failed_count}")
    print("="*80)

if __name__ == '__main__':
    main()
