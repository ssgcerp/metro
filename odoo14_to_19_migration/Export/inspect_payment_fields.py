
import json
import random
import sys
import requests
import argparse

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
            return response.json()
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
        return result.get('result')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--db', required=True)
    parser.add_argument('--user', required=True)
    parser.add_argument('--password', required=True)
    args = parser.parse_args()

    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    if not client.authenticate():
        print("Auth Failed")
        sys.exit(1)

    print("Connected. Fetching fields for account.payment...")
    
    # fields_get
    fields_info = client.execute_kw('account.payment', 'fields_get', [], {'attributes': ['string', 'type']})
    
    if fields_info:
        print(f"Found {len(fields_info)} fields.")
        
        # Check specific fields of interest
        check_list = ['ref', 'memo', 'payment_method_id', 'payment_method_line_id', 'journal_id']
        for f in check_list:
            if f in fields_info:
                print(f"Field '{f}': {fields_info[f]}")
            else:
                print(f"Field '{f}': NOT FOUND")
                
        # Also print all fields starting with 'reconciled'
        print("\n--- Reconciled Fields ---")
        for f in fields_info:
            if 'reconciled' in f:
                print(f"{f}: {fields_info[f]}")

if __name__ == "__main__":
    main()
