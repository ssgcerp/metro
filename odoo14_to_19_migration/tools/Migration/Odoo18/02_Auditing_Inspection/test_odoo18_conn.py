import json
import requests
import random

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
            response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers, timeout=30)
            return response.json()
        except Exception as e:
            print(f"Error: {e}")
            return None

    def authenticate(self):
        params = {"db": self.db, "login": self.username, "password": self.password}
        result = self.json_rpc("/web/session/authenticate", params)
        if result and 'result' in result and 'uid' in result['result']:
            self.uid = result['result']['uid']
            return True
        print(f"Auth failed: {result}")
        return False

    def execute_kw(self, model, method, args=None, kwargs=None):
        if args is None: args = []
        if kwargs is None: kwargs = {}
        params = {"model": model, "method": method, "args": args, "kwargs": kwargs}
        result = self.json_rpc("/web/dataset/call_kw", params)
        return result.get('result')

# Credentials from export_odoo18_vendor_bills.py
url = 'https://metro-fire-system-llc.odoo.com'
db = 'metro-fire-system-llc'
user = 'sruthi@metrofiresystems.com'
password = 'Sruthi@321'

print(f"Connecting to {url}...")
client = OdooJsonRpcClient(url, db, user, password)
if client.authenticate():
    print("Authentication Successful!")
    count = client.execute_kw('account.move', 'search_count', [[('move_type', '=', 'in_invoice')]])
    print(f"Total Vendor Bills in Odoo 18: {count}")
    
    # Check posted
    posted_count = client.execute_kw('account.move', 'search_count', [[('move_type', '=', 'in_invoice'), ('state', '=', 'posted')]])
    print(f"Posted Vendor Bills in Odoo 18: {posted_count}")
else:
    print("Authentication Failed!")
