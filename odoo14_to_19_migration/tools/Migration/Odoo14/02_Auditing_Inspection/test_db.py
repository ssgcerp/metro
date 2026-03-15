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

    def json_rpc(self, endpoint, params):
        data = {"jsonrpc": "2.0", "method": "call", "params": params, "id": random.randint(0, 1000000000)}
        headers = {"Content-Type": "application/json"}
        response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers, timeout=30)
        return response.json()

    def authenticate(self):
        params = {"db": self.db, "login": self.username, "password": self.password}
        res = self.json_rpc("/web/session/authenticate", params)
        if res and "result" in res and "uid" in res["result"]:
            return True
        return False

    def execute_kw(self, model, method, args=None, kwargs=None):
        if args is None: args = []
        if kwargs is None: kwargs = {}
        params = {"model": model, "method": method, "args": args, "kwargs": kwargs}
        res = self.json_rpc("/web/dataset/call_kw", params)
        if res and "error" in res:
             print(f"Error: {res['error']}")
             return None
        return res.get("result")

print('Checking metrodb (Source)...')
src = OdooJsonRpcClient('https://metro.equdaierp.com', 'metrodb', 'admin', 'Amaze@321')
if src.authenticate():
    companies = src.execute_kw('res.company', 'search_read', [[]], {'fields': ['id', 'name']})
    print('\nmetrodb Companies:')
    for c in companies: print(f" - {c['id']}: {c['name']}")
    
    # Get payments journals
    journals = src.execute_kw('account.journal', 'search_read', [[('type', 'in', ['bank', 'cash'])]], {'fields': ['id', 'name', 'company_id', 'code']})
    print('\nmetrodb Bank/Cash Journals:')
    for j in journals: print(f" - {j['id']}: {j['name']} ({j['code']}) - Company: {j['company_id'][1] if j['company_id'] else ''}")
else:
    print('Failed to auth metrodb')

print('\n----------------------------------\n')

print('Checking newdb (Destination)...')
dest = OdooJsonRpcClient('https://metro.equdaierp.com', 'newdb', 'admin', 'Amaze@321')
if dest.authenticate():
    companies = dest.execute_kw('res.company', 'search_read', [[]], {'fields': ['id', 'name']})
    print('\nnewdb Companies:')
    for c in companies: print(f" - {c['id']}: {c['name']}")
    
    # Get payments journals
    journals = dest.execute_kw('account.journal', 'search_read', [[('type', 'in', ['bank', 'cash'])]], {'fields': ['id', 'name', 'company_id', 'code']})
    print('\nnewdb Bank/Cash Journals:')
    for j in journals: print(f" - {j['id']}: {j['name']} ({j['code']}) - Company: {j['company_id'][1] if j['company_id'] else ''}")
else:
    print('Failed to auth newdb')
