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
        return result.get('result')

def main():
    parser = argparse.ArgumentParser(description='Report Skipped Accounts')
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    default_list_path = os.path.join(base_dir, 'Export', 'Unique_Accounts_List.txt')
    parser.add_argument('--file', default=default_list_path, help='Path to Unique Accounts List')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Dest Odoo 19 URL')
    parser.add_argument('--db', default='metrodb', help='Dest Odoo 19 User')
    parser.add_argument('--user', default='admin', help='Dest Odoo 19 User')
    parser.add_argument('--password', default='Amaze@321', help='Dest Odoo 19 Password')

    args = parser.parse_args()

    accounts_to_process = {}
    with open(args.file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split(' ', 1)
            accounts_to_process[parts[0]] = parts[1] if len(parts) > 1 else "Unknown"

    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    client.authenticate()
    
    companies = client.execute_kw('res.company', 'search_read', [[], ['name']])
    company_ids = [c['id'] for c in companies]
    
    # Re-auth with full company access (just in case)
    try:
        client.execute_kw('res.users', 'write', [[client.uid], {'company_ids': [(6, 0, company_ids)]}])
        client.authenticate() # Refresh session
    except: pass

    ctx = {'allowed_company_ids': company_ids, 'active_test': False, 'check_company': False}
    search_ctx = {'active_test': False}

    print("\n--- Analysis of Skipped Accounts ---")
    skipped_list = []

    for code, name in accounts_to_process.items():
        domain = [('code', '=', code)]
        existing_accounts = client.execute_kw('account.account', 'search_read', [domain, ['id', 'name', 'company_ids']], {'context': search_ctx})
        
        if not existing_accounts:
            # Would be Created (Not Skipped)
            pass
        else:
            primary_acc = existing_accounts[0]
            account_id = primary_acc['id']
            
            # Check coverage
            companies_covered_by_others = set()
            for acc in existing_accounts:
                if acc['id'] != account_id:
                    for cid in acc['company_ids']:
                        companies_covered_by_others.add(cid)
            
            # Target Set: Companies NOT covered by secondary accounts
            target_ids = [cid for cid in company_ids if cid not in companies_covered_by_others]
            
            # If target_ids includes companies NOT currently in primary_acc, it's an Update.
            # If target_ids == primary_acc.company_ids (logic in previous script was flawed slightly?
            # Wait, if target_ids (all allowed) is same as primary coverage, then we are just refreshing mapping.
            
            # The ONLY case strict "Skip" happens usually if:
            # 1. We decided not to update because of some logic?
            # Actually, my previous script logic was:
            # if not existing: Create
            # else: Update Primary
            # It only printed "ALREADY COVERED" if the 'target_company_ids' (calculated differently there) was empty.
            
            # Replicating EXACT logic from migration script to identify 'Pending'
            current_visibility = set(primary_acc['company_ids'])
            
            # Logic from migration script:
            # allowed_target_ids = [cid for cid in company_ids if cid not in companies_covered_by_others]
            # write allowed_target_ids
            # This is ALWAYS an update unless allowed_target_ids is empty? (Impossible if company_ids > 0)
            
            # Wait, did I actually skip anything in the final script?
            # The final script FORCE UPDATES mappings for `allowed_target_ids`.
            # So if it reported 67 updated, maybe the other 18 FAILED or had NO CHANGES?
            
            # Let's inspect conflicting companies specifically.
            if companies_covered_by_others:
                 skipped_list.append({
                     'code': code, 
                     'name': name,
                     'reason': 'Conflicting duplicates exist',
                     'conflicts': len(companies_covered_by_others)
                 })
    
    print(f"\nFound {len(skipped_list)} accounts with conflicts/duplicates:")
    for item in skipped_list:
        print(f"- {item['code']} {item['name']} (Shared with {item['conflicts']} other accounts)")
        
if __name__ == '__main__':
    main()
