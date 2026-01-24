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
        except: return None

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
    parser = argparse.ArgumentParser(description='Report Coverage Gaps')
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    default_list_path = os.path.join(base_dir, 'Export', 'Unique_Accounts_List.txt')
    parser.add_argument('--file', default=default_list_path)
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()

    # 1. Read Accounts
    accounts_to_process = {}
    with open(args.file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                p = line.strip().split(' ', 1)
                accounts_to_process[p[0]] = p[1] if len(p)>1 else "Unknown"

    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    client.authenticate()
    
    # Enable full access
    companies = client.execute_kw('res.company', 'search_read', [[], ['name']])
    total_companies = len(companies)
    company_ids = [c['id'] for c in companies]
    
    try:
        client.execute_kw('res.users', 'write', [[client.uid], {'company_ids': [(6, 0, company_ids)]}])
        client.authenticate()
    except: pass
    
    print(f"\n--- Coverage Analysis (Total Companies: {total_companies}) ---")
    
    pending_list = []
    
    ctx = {'active_test': False} # Check archives too
    
    for code, name in accounts_to_process.items():
        # Search ALL accounts with this code
        domain = [('code', '=', code)]
        accounts = client.execute_kw('account.account', 'search_read', [domain, ['company_ids']], {'context': ctx})
        
        covered_companies = set()
        for acc in accounts:
            for cid in acc['company_ids']:
                covered_companies.add(cid)
                
        coverage_count = len(covered_companies)
        
        if coverage_count < total_companies:
            missing = [c['name'] for c in companies if c['id'] not in covered_companies]
            
            # Check if mappings exist?
            # Ideally account.company_ids should reflect mappings if we used code match.
            # But technically mappings are deeper. 
            # However, my script UPDATES company_ids. So if company_ids is partial, the script failed/skipped.
            
            pending_list.append({
                'code': code,
                'name': name,
                'covered': coverage_count,
                'missing_count': total_companies - coverage_count,
                'missing_names': missing
            })

    print(f"\nFound {len(pending_list)} Pending/Partial Accounts:")
    for item in pending_list:
        print(f"[PENDING] {item['code']} {item['name']}")
        print(f"  - Covered: {item['covered']}/{total_companies}")
        print(f"  - Missing in: {', '.join(item['missing_names'][:5])}...")

if __name__ == '__main__':
    main()
