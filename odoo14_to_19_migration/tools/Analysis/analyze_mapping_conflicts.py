import argparse
import requests
import json
import random
import os

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
        except Exception:
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
        return result.get('result') if (result := self.json_rpc("/web/dataset/call_kw", params)) else None

def main():
    parser = argparse.ArgumentParser(description='Analyze Mapping Conflicts')
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    default_list_path = os.path.join(base_dir, 'Export', 'Unique_Accounts_List.txt')
    parser.add_argument('--file', default=default_list_path, help='Path')
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()

    # 1. Read Codes
    accounts_to_process = {}
    with open(args.file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                p = line.strip().split(' ', 1)
                accounts_to_process[p[0]] = p[1] if len(p)>1 else "Unknown"

    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    client.authenticate()
    
    print("\n--- Analysing Mapping Conflicts ---")
    
    # 2. Iterate codes
    conflicts_found = 0
    ctx = {'active_test': False} # Find even in archives
    
    for code, name in accounts_to_process.items():
        # A. Find the Intended Code Owner (Main Account)
        owner_domain = [('code', '=', code)]
        owners = client.execute_kw('account.account', 'search_read', [owner_domain, ['id', 'name']], {'context': ctx})
        
        intended_owner_id = owners[0]['id'] if owners else None
        
        # B. Find Mappings for this Code
        mapping_domain = [('code', '=', code)]
        mappings = client.execute_kw('account.code.mapping', 'search_read', [mapping_domain, ['account_id', 'company_id']], {'context': ctx})
        
        # C. Check for Mappings pointing to OTHER accounts
        conflict_details = []
        
        for m in mappings or []:
            mapped_acc_id = m['account_id'][0] if m['account_id'] else None
            # If mapping points to a DIFFERENT account than our intended owner -> CONFLICT
            if mapped_acc_id and mapped_acc_id != intended_owner_id:
                # Get Name of conflicting account
                conflict_acc = client.execute_kw('account.account', 'read', [[mapped_acc_id], ['name', 'code']], {'context': ctx})
                conflict_name = conflict_acc[0]['name'] if conflict_acc else 'Unknown'
                conflict_code = conflict_acc[0]['code'] if conflict_acc else 'Unknown'
                
                comp_name = m['company_id'][1] if m['company_id'] else 'Unknown'
                
                conflict_details.append(f"{comp_name}: Mapped to '{conflict_name}' ({conflict_code})")

        if conflict_details:
             conflicts_found += 1
             print(f"\n[PENDING] {code} {name}")
             print("  Reason: Code is already used in mappings by other accounts:")
             for d in  list(set(conflict_details))[:5]: # limit output
                 print(f"    - {d}")

    print(f"\nTotal Conflicting/Pending Accounts: {conflicts_found}")

if __name__ == '__main__':
    main()
