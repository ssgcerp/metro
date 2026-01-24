import argparse
import requests
import json
import random
import os
import sys

# -----------------------------------------------------------------------------
# Odoo JSON-RPC Client
# -----------------------------------------------------------------------------
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
            response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers, timeout=60)
            return response.json()
        except Exception as e:
            print(f"RPC Connection Failed: {e}")
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
             print(f"RPC Error ({method}): {result['error']}")
             return None
        return result.get('result')

# -----------------------------------------------------------------------------
# Main Script
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='Migrate Shared Accounts to Odoo 19')
    
    # Path to Unique Accounts List
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    default_list_path = os.path.join(base_dir, 'Export', 'Unique_Accounts_List.txt')
    
    parser.add_argument('--file', default=default_list_path, help='Path to Unique Accounts List')
    
    # Odoo 19 Credentials
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Dest Odoo 19 URL')
    parser.add_argument('--db', default='metrodb', help='Dest Odoo 19 User')
    parser.add_argument('--user', default='admin', help='Dest Odoo 19 User')
    parser.add_argument('--password', default='Amaze@321', help='Dest Odoo 19 Password')

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        return

    # 1. Read Accounts List
    print(f"Reading {args.file}...")
    accounts_to_process = {} # code -> name
    
    with open(args.file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Simple parsing: "Code Name"
            parts = line.split(' ', 1)
            code = parts[0]
            name = parts[1] if len(parts) > 1 else "Unknown Account"
            
            # Store (last one wins if duplicate, but usually codes are unique-ish per purpose)
            # Actually, per user request, we preserve existing account name if it exists.
            if code not in accounts_to_process:
                accounts_to_process[code] = name
                
    print(f"Parsed {len(accounts_to_process)} unique account codes.")

    # 2. Connect to Odoo 19
    print(f"\nConnecting to {args.url}...")
    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    if not client.authenticate():
        print("Authentication Failed!")
        return
        
    # 3. Fetch All Companies
    print("Fetching Companies...")
    companies = client.execute_kw('res.company', 'search_read', [[], ['name']])
    if not companies:
        print("No companies found?")
        return
        
    company_ids = [c['id'] for c in companies]
    print(f"Found {len(companies)} companies: {', '.join([c['name'] for c in companies])}")

    # 3b. Ensure Admin has access to ALL companies
    print("Granting 'admin' access to all companies...")
    try:
        # Write to current user (client.uid)
        client.execute_kw('res.users', 'write', [[client.uid], {'company_ids': [(6, 0, company_ids)]}])
        print("Access granted to all companies.")
        
        # Re-authenticate to ensure session is fresh with new rights
        if not client.authenticate():
             print("Re-authentication failed!")
             return
             
    except Exception as e:
        print(f"Warning: Could not update admin companies: {e}")

    # 4. Process Accounts
    print("\nProcessing Accounts...")
    
    updated_count = 0
    created_count = 0
    skipped_count = 0
    
    # Context with all companies
    # active_test=False to find archived accounts too
    # check_company=False to ignore company consistency checks during search
    ctx = {'allowed_company_ids': company_ids, 'active_test': False, 'check_company': False}

    for code, name in accounts_to_process.items():
        print(f"Processing Code: {code}...", end='')
        
        domain = [('code', '=', code)]
        search_ctx = {'active_test': False} 
        
        # Find ALL accounts with this code (including Archived)
        # We need to find valid collisions even if archived.
        search_ctx = {'active_test': False}
        existing_accounts = client.execute_kw('account.account', 'search_read', [domain, ['id', 'name', 'company_ids']], {'context': search_ctx})
        
        used_company_ids = set()
        for acc in existing_accounts:
            for cid in acc['company_ids']:
                used_company_ids.add(cid)
        
        # Companies that need coverage
        target_company_ids = [cid for cid in company_ids if cid not in used_company_ids]
        
        if not existing_accounts:
            # CASE 1: No account exists. Create new Shared for ALL companies.
            print(f" [MISSING -> Creating Shared]")
            acc_type = 'asset_current'
            if code.startswith('1'): acc_type = 'asset_current'
            elif code.startswith('2'): acc_type = 'liability_current'
            elif code.startswith('3'): acc_type = 'equity'
            elif code.startswith('4'): acc_type = 'expense'
            elif code.startswith('5'): acc_type = 'income'
            elif code.startswith('6'): acc_type = 'expense'
            
            mapping_ops = []
            for cid in company_ids:
                mapping_ops.append((0, 0, {'company_id': cid, 'code': code}))
            
            vals = {
                'code': code,
                'name': name,
                'account_type': acc_type,
                'company_ids': [(6, 0, company_ids)],
                'code_mapping_ids': mapping_ops
            }
            res = client.execute_kw('account.account', 'create', [vals], {'context': ctx})
            if res: created_count += 1
            else: print(" [FAILED CREATE]")

        else:
            # CASE 2: Accounts exist (One or Many).
            # We focus on the FIRST account found (Primary).
            # We want to ensure it has MAPPINGS for all usage companies.
            
            primary_acc = existing_accounts[0]
            account_id = primary_acc['id']

            # Companies this specific account ALREADY covers (visibility)
            current_visibility = set(primary_acc['company_ids'])
            
            # Companies we WANT it to cover
            # = (Current Visibility) + (Any companies NOT covered by ANY existing account)
            # We must NOT try to cover a company that is covered by a DIFFERENT account (duplicate conflict)
            
            # Re-calculating coverage to be safe
            companies_covered_by_others = set()
            for acc in existing_accounts:
                if acc['id'] != account_id:
                    for cid in acc['company_ids']:
                        companies_covered_by_others.add(cid)
            
            # Allowed Targets: All Companies - CoveredByOthers
            # logic: If Company X has Account B, we cannot add Company X to Account A.
            
            allowed_target_ids = [cid for cid in company_ids if cid not in companies_covered_by_others]
            
            # So the new visibility list for Primary Account should be Allowed Targets
            # (which naturally includes its own current visibility)
            
            # Fetch existing mappings for Primary Account
            acc_detail = client.execute_kw('account.account', 'read', [[account_id], ['code_mapping_ids']], {'context': ctx})
            mapping_ids = acc_detail[0]['code_mapping_ids'] if acc_detail else []
            existing_maps = {}
            if mapping_ids:
                maps_data = client.execute_kw('account.code.mapping', 'read', [mapping_ids, ['company_id']], {'context': ctx})
                if maps_data:
                    for m in maps_data:
                        c_id = m['company_id'][0] if m['company_id'] else False
                        if c_id: existing_maps[c_id] = m['id']

            mapping_ops = []
            # Update mappings for all Allowed Targets
            for cid in allowed_target_ids:
                if cid in existing_maps:
                    # Explicitly updated code to ensure it's not empty
                    mapping_ops.append((1, existing_maps[cid], {'code': code}))
                else:
                    mapping_ops.append((0, 0, {'company_id': cid, 'code': code}))
            
            vals = {
                'company_ids': [(6, 0, allowed_target_ids)],
                'code_mapping_ids': mapping_ops
            }
            
            res = client.execute_kw('account.account', 'write', [[account_id], vals], {'context': ctx})
            if res: 
                print(f" [UPDATED/EXTENDED]")
                updated_count += 1
            else:
                print(" [FAILED UPDATE]")

                
    print(f"\nSummary:")
    print(f"  Updated: {updated_count}")
    print(f"  Created: {created_count}")
    print(f"  Total  : {len(accounts_to_process)}")

if __name__ == '__main__':
    main()
