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
            print(f"RPC Error to {self.url}: {e}")
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

def fetch_po_names(client, system_name):
    print(f"Fetching POs from {system_name}...")
    
    # We only need the Names
    # If huge number, might need batching, but usually search_read handles decent size or returns IDs first.
    # search_read might fail on huge datasets. Let's do search then read in batches or just search for names?
    # 'search_read' with only 'name' field is usually efficient.
    
    # Let's check count first
    count = client.execute_kw('purchase.order', 'search_count', [[]])
    print(f"  Found {count} POs in {system_name}.")
    
    if not count:
        return set()
        
    # Batch fetch
    batch_size = 1000
    all_names = set()
    
    ids = client.execute_kw('purchase.order', 'search', [[]])
    if not ids: return set()
    
    total = len(ids)
    for i in range(0, total, batch_size):
        batch = ids[i:i+batch_size]
        res = client.execute_kw('purchase.order', 'read', [batch, ['name']])
        if res:
            for r in res:
                if r.get('name'):
                    all_names.add(r['name'])
        print(f"  Fetched {len(all_names)}/{total}...", end='\r')
    print()
    return all_names

def main():
    parser = argparse.ArgumentParser(description='Check Missing POs')
    
    # Defaults
    parser.add_argument('--o14-url', default='https://erpmfs.com')
    parser.add_argument('--o14-db', default='metro_production_8_8_22')
    parser.add_argument('--o14-user', default='Sales.auh@metrofiresystems.com')
    parser.add_argument('--o14-pass', default='Sales@185734')
    
    parser.add_argument('--o19-url', default='https://metro.equdaierp.com')
    parser.add_argument('--o19-db', default='metrodb')
    parser.add_argument('--o19-user', default='admin')
    parser.add_argument('--o19-pass', default='Amaze@321')
    
    args = parser.parse_args()

    # 1. Odoo 14
    client14 = OdooJsonRpcClient(args.o14_url, args.o14_db, args.o14_user, args.o14_pass)
    if not client14.authenticate():
        print("Failed to auth with Odoo 14")
        return

    # 2. Odoo 19
    client19 = OdooJsonRpcClient(args.o19_url, args.o19_db, args.o19_user, args.o19_pass)
    if not client19.authenticate():
        print("Failed to auth with Odoo 19")
        return

    # 3. Fetch
    names14 = fetch_po_names(client14, "Odoo 14")
    names19 = fetch_po_names(client19, "Odoo 19")
    
    # 4. Compare
    missing = names14 - names19
    
    print(f"\nAnalysis Results:")
    print(f"  Odoo 14 Total: {len(names14)}")
    print(f"  Odoo 19 Total: {len(names19)}")
    print(f"  Missing in 19: {len(missing)}")
    
    # 5. Write Report
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    export_dir = os.path.join(base_dir, 'Export')
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
        
    out_file = os.path.join(export_dir, 'Missing_Purchase_Orders.txt')
    
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write("Missing Purchase Orders (In Odoo 14 but not Odoo 19)\n")
        f.write("===================================================\n")
        for name in sorted(missing):
            f.write(f"{name}\n")
            
    print(f"\nReport saved to: {out_file}")

if __name__ == '__main__':
    main()
