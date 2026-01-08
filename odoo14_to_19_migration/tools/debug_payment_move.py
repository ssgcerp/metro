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
            res_json = response.json()
            if 'error' in res_json:
                print(f"RPC ERROR: {res_json['error']}")
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
             return None
        return result.get('result')

def main():
    url = "http://localhost:8079"
    db = "metrodb"
    username = "admin"
    password = "Amaze@321"

    client = OdooJsonRpcClient(url, db, username, password)
    if not client.authenticate():
        print("Auth failed.")
        return

    print("Reading Payment ID 14...")
    res = client.execute_kw('account.payment', 'read', [[14]], {'fields': ['name', 'state', 'move_id', 'memo', 'amount', 'payment_method_line_id', 'journal_id']})
    
    if res:
        print(json.dumps(res, indent=2))
        payment = res[0]
        
        # Check Move
        if payment.get('move_id'):
            move_id = payment['move_id'][0]
            print(f"\nMove ID found: {move_id}. Reading lines...")
            lines = client.execute_kw('account.move.line', 'search_read', [[('move_id', '=', move_id)]], {'fields': ['account_id', 'debit', 'credit', 'reconciled']})
            print(json.dumps(lines, indent=2))
    else:
        print("Payment not found or read error.")

if __name__ == "__main__":
    main()
