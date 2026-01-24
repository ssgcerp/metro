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
                # print(f"RPC ERROR: {res_json['error']}") # Verbose
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
             raise Exception(result['error']['data']['message'] if 'data' in result['error'] else result['error']['message'])
        return result.get('result')

def main():
    parser = argparse.ArgumentParser(description='Migrate Expense Vouchers from Odoo 14 to Odoo 19')
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
    print(f"MIGRATING EXPENSE VOUCHERS")
    print(f"Source: {args.src_url} ({args.src_db})")
    print(f"Dest  : {args.dest_url} ({args.dest_db})")
    print("="*80)

    # 1. Connect
    src_client = OdooJsonRpcClient(args.src_url, args.src_db, args.src_user, args.src_password)
    if not src_client.authenticate():
        print("Failed to authenticate with Source Odoo 14")
        sys.exit(1)
    print("Connected to Source.")

    dest_client = OdooJsonRpcClient(args.dest_url, args.dest_db, args.dest_user, args.dest_password)
    if not dest_client.authenticate():
        print("Failed to authenticate with Destination Odoo 19")
        sys.exit(1)
    print("Connected to Destination.")

    # 2. Fetch Source Vouchers
    # Filter out cancelled? Or migate all? Let's just migrate everything.
    print("Fetching Expense Vouchers from Source...")
    
    # Fields to fetch
    fields_v14 = [
        'name', 'partner_id', 'journal_id', 'date', 'voucher_type',
        'reference', 'comments', 'currency_id', 'state', 'expense_line_ids', 'branch_id'
    ]
    
    try:
        vouchers_v14 = src_client.execute_kw('account.expense.voucher', 'search_read', [[], fields_v14])
    except Exception as e:
        print(f"Error fetching source vouchers: {e}")
        sys.exit(1)

    print(f"Found {len(vouchers_v14)} vouchers in Source.")
    
    if args.limit > 0:
        vouchers_v14 = vouchers_v14[:args.limit]
        print(f"Limiting to first {args.limit}.")

    count_created = 0
    count_skipped = 0
    count_failed = 0

    # Cache for Lookups
    # (Name -> ID)
    partner_map = {}
    journal_map = {}
    currency_map = {}
    account_map = {} # Code -> ID
    tax_map = {} # Name -> ID
    project_map = {} # Name -> ID
    company_map = {} # Name -> ID

    # Helper functions for lookup
    def get_dest_partner_id(name):
        if not name: return False
        if name in partner_map: return partner_map[name]
        # Search
        res = dest_client.execute_kw('res.partner', 'search', [[('name', '=', name)]], {'limit': 1})
        if res:
            partner_map[name] = res[0]
            return res[0]
        return False # Or Create? Better to fail/skip or log warning.

    def get_dest_journal_id(name):
        if not name: return False
        if name in journal_map: return journal_map[name]
        res = dest_client.execute_kw('account.journal', 'search', [[('name', '=', name)]], {'limit': 1})
        if res:
            journal_map[name] = res[0]
            return res[0]
        return False
        
    def get_dest_currency_id(name):
        if not name: return False
        if name in currency_map: return currency_map[name]
        res = dest_client.execute_kw('res.currency', 'search', [[('name', '=', name)]], {'limit': 1})
        if res:
            currency_map[name] = res[0]
            return res[0]
        return False

    def get_dest_account_id(code):
        if not code: return False
        if code in account_map: return account_map[code]
        res = dest_client.execute_kw('account.account', 'search', [[('code', '=', code)]], {'limit': 1})
        if res:
            account_map[code] = res[0]
            return res[0]
        return False

    def get_dest_tax_id(name):
        if not name: return False
        if name in tax_map: return tax_map[name]
        res = dest_client.execute_kw('account.tax', 'search', [[('name', '=', name)]], {'limit': 1})
        if res:
            tax_map[name] = res[0]
            return res[0]
        return False
        
    def get_dest_project_id(name):
        if not name: return False
        if name in project_map: return project_map[name]
        
        # 1. Exact Match
        res = dest_client.execute_kw('project.project', 'search', [[('name', '=', name)]], {'limit': 1})
        if res:
            project_map[name] = res[0]
            return res[0]
            
        # 2. Case Insensitive Exact Match
        res = dest_client.execute_kw('project.project', 'search', [[('name', '=ilike', name)]], {'limit': 1})
        if res:
            project_map[name] = res[0]
            return res[0]

        import re
        
        # 3. Match by Project Code (if present in name like [CODE] Name)
        # Odoo 14 often displays [Code] Name
        match = re.match(r'^\[(.*?)\]', name)
        if match:
            code = match.group(1)
            # Search by project_code
            res = dest_client.execute_kw('project.project', 'search', [[('project_code', '=', code)]], {'limit': 1})
            if res:
                project_map[name] = res[0]
                return res[0]

        # 4. Substring Match (V19 name contains V14 name)
        # Use simple ilike. e.g. V14="Project A", V19="[123] Project A" -> Match
        # e.g. V14="[123] Project A", V19="Project A" -> No Match (search term longer than target)
        if len(name) > 3: # Avoid matching short common strings
            res = dest_client.execute_kw('project.project', 'search', [[('name', 'ilike', name)]], {'limit': 1})
            if res:
                project_map[name] = res[0]
                return res[0]
                
        return False

    def get_dest_company_id(name):
        if not name: return False
        if name in company_map: return company_map[name]
        res = dest_client.execute_kw('res.company', 'search', [[('name', '=', name)]], {'limit': 1})
        if res:
            company_map[name] = res[0]
            return res[0]
        # Try case insensitive
        res = dest_client.execute_kw('res.company', 'search', [[('name', '=ilike', name)]], {'limit': 1})
        if res:
            company_map[name] = res[0]
            return res[0]
        return False

    # 3. Iterate
    for v in vouchers_v14:
        v_name = v['name']
        print(f"Processing {v_name}...")

        # Check existing
        try:
            existing = dest_client.execute_kw('account.expense.voucher', 'search_count', [[('name', '=', v_name)]])
            if existing > 0:
                print(f"  Skipping {v_name} (Already exists)")
                count_skipped += 1
                continue
        except Exception as e:
            print(f"  Check failed: {e}")
            count_failed += 1
            continue

        # Prepare Header Vals
        vals = {
            'name': v_name,
            'date': v['date'],
            'voucher_type': v['voucher_type'],
            'reference': v['reference'] or '',
            'comments': v['comments'] or '',
            'state': 'draft' # Always create draft first
        }

        # Map Relationships
        # Partner
        p_name = v['partner_id'][1] if v['partner_id'] else False
        if p_name:
            pid = get_dest_partner_id(p_name)
            if pid: vals['partner_id'] = pid
            else: print(f"  WARNING: Partner '{p_name}' not found.")
        
        # Journal
        j_name = v['journal_id'][1] if v['journal_id'] else False
        if j_name:
            jid = get_dest_journal_id(j_name)
            if jid: vals['journal_id'] = jid
            else: print(f"  WARNING: Journal '{j_name}' not found.")
        
        # Currency
        c_name = v['currency_id'][1] if v['currency_id'] else False
        if c_name:
            cid = get_dest_currency_id(c_name)
            if cid: vals['currency_id'] = cid
        
        # Branch -> Company
        b_name = v['branch_id'][1] if v['branch_id'] else False
        if b_name:
            comp_id = get_dest_company_id(b_name)
            if comp_id: vals['company_id'] = comp_id
            else: print(f"  WARNING: Company for Branch '{b_name}' not found.")
        
        # Lines
        line_ids = v['expense_line_ids']
        lines_data = []
        if line_ids:
             line_fields = ['account_id', 'label', 'price_amount', 'tax_id', 'project_id']
             lines_v14 = src_client.execute_kw('account.expense.voucher.line', 'read', [line_ids, line_fields])
             
             for l in lines_v14:
                 l_vals = {
                     'label': l['label'],
                     'price_amount': l['price_amount'],
                 }
                 
                 # Account (Crucial - Map by Code if possible, usually [1] is 'Code Name')
                 # But v14 read returns [ID, "Code Name"]. We can split.
                 acc_display = l['account_id'][1] if l['account_id'] else ''
                 acc_code = acc_display.split(' ')[0] if acc_display else False
                 
                 if acc_code:
                     aid = get_dest_account_id(acc_code)
                     if aid: l_vals['account_id'] = aid
                     else: print(f"  WARNING: Account '{acc_code}' not found.")
                 
                 # Tax
                 t_name = l['tax_id'][1] if l['tax_id'] else False
                 if t_name:
                     tid = get_dest_tax_id(t_name)
                     if tid: l_vals['tax_id'] = tid
                     
                 # Project
                 proj_name = l['project_id'][1] if l['project_id'] else False
                 if proj_name:
                     proj_id = get_dest_project_id(proj_name)
                     if proj_id: l_vals['project_id'] = proj_id
                     else: print(f"  WARNING: Project '{proj_name}' not found.")
                 
                 lines_data.append((0, 0, l_vals))
        
        vals['expense_line_ids'] = lines_data

        # Create
        try:
            dest_client.execute_kw('account.expense.voucher', 'create', [vals])
            print(f"  Created {v_name}.")
            count_created += 1
            
            # Post if needed
            if v['state'] == 'posted':
                # Try to post? Maybe skip to avoid errors initially.
                # Or just update state to posted? No, action_post does entries.
                # User might want to post manually.
                pass 
                
        except Exception as e:
            print(f"  Creation FAILED for {v_name}: {e}")
            count_failed += 1

    print("\n" + "="*80)
    print(f"Migration Complete.")
    print(f"Created: {count_created}")
    print(f"Skipped: {count_skipped}")
    print(f"Failed : {count_failed}")
    print("="*80)

if __name__ == '__main__':
    main()
