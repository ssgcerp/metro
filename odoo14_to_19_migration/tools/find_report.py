import json
import random
import requests
import sys

# Configuration
URL = 'https://metro.equdaierp.com'
DB = 'metrodb'
USER = 'admin'
PASSWORD = 'Amaze@321'

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
            response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers)
            return response.json()
        except Exception as e:
            print(f"RPC Error: {e}")
            return {}

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
        if result.get('error'):
            print(f"RPC Error ({method}): {result['error']}")
            return None
        return result.get('result')

def main():
    print("Connecting...")
    client = OdooJsonRpcClient(URL, DB, USER, PASSWORD)
    if not client.authenticate():
        print("Authentication Failed")
        return
    print("Authenticated.")

    # Search for All Reports with VAT or Tax
    print("Searching for 'VAT' or 'Tax' reports...")
    reports = client.execute_kw('account.report', 'search_read', 
        [['|', ('name', 'ilike', 'VAT'), ('name', 'ilike', 'Tax')]], 
        {'fields': ['id', 'name', 'filter_multi_company']})
    
    if reports:
        for r in reports:
            print(f"Report: {r['name']} (ID: {r['id']}) MultiCompany: {r.get('filter_multi_company')}")
            # Get External ID?
            # It's hard via RPC directly unless we search ir.model.data.
            # But ID is enough if we use it, but code should ideally be stable.
            # Let's try to get XML ID
            xml_id = client.execute_kw('ir.model.data', 'search_read', 
                [[('model', '=', 'account.report'), ('res_id', '=', r['id'])]], 
                {'fields': ['module', 'name']})
            if xml_id:
                print(f"  -> XML ID: {xml_id[0]['module']}.{xml_id[0]['name']}")
    else:
        print("Report not found!")

if __name__ == "__main__":
    main()
