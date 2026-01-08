import requests
import json
import argparse
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
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
            "id": 1,
        }
        headers = {"Content-Type": "application/json"}
        try:
            response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers, timeout=300)
            res_json = response.json()
            return res_json
        except Exception as e:
            _logger.error(f"RPC EXCEPTION: {e}")
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
             print(result['error'])
             return None
        return result.get('result')

def main():
    parser = argparse.ArgumentParser(description='Inspect Payment')
    parser.add_argument('--name', required=True, help='Payment Name to find')
    args = parser.parse_args()

    client = OdooJsonRpcClient('http://localhost:8079', 'metrodb', 'admin', 'Amaze@321')
    
    if not client.authenticate():
        print("Auth failed")
        return

    # Setup Context
    all_companies = client.execute_kw('res.company', 'search', [[]])
    context = {'allowed_company_ids': all_companies}
    
    print(f"Searching for {args.name}...")
    kw = {'fields': ['id', 'name', 'state', 'partner_type', 'company_id', 'is_reconciled', 'move_id'], 'context': context}
    payments = client.execute_kw('account.payment', 'search_read', 
        [[('name', '=', args.name)]], 
        kwargs=kw
    )
    
    if payments:
        print(f"FOUND: {payments[0]}")
    else:
        print("NOT FOUND")
        # Try finding without partner_type filter using pure search
        all_pay = client.execute_kw('account.payment', 'search_read', [[('name', 'ilike', args.name)]], kwargs={'context': context})
        print(f"Broad Search Result: {all_pay}")

if __name__ == '__main__':
    main()
