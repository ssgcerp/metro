import argparse
import sys
import json
import requests
import pprint

class JSONRPCClient:
    def __init__(self, url, db, user, password):
        self.url = url
        self.db = db
        self.user = user
        self.password = password
        self.session_id = None
        self.uid = None

    def json_rpc(self, endpoint, params):
        data = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": params,
            "id": 1
        }
        headers = {"Content-Type": "application/json"}
        if self.session_id:
            headers["Cookie"] = f"session_id={self.session_id}"
        
        response = requests.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers)
        result = response.json()
        if 'error' in result:
             # simple raise
             raise Exception(result['error']['data']['message'])
        return result

    def authenticate(self):
        params = {
            "db": self.db,
            "login": self.user,
            "password": self.password
        }
        res = self.json_rpc("/web/session/authenticate", params)
        self.session_id = requests.utils.dict_from_cookiejar(requests.Response().cookies).get('session_id') # Fake cookie logic?
        # Actually session is in response headers usually
        # But /authenticate returns session_id in result usually
        # For simplicity, let's just use the returned session_id if available or just rely on requests session if we used one.
        # But here I am using requests.post repeatedly.
        # Odoo JSON-RPC usually sets a cookie.
        # Let's use a Session object.
        pass

# Re-implementation using Requests Session for cookies handling
class OdooClient:
    def __init__(self, url, db, user, password):
        self.url = url
        self.db = db
        self.user = user
        self.password = password
        self.session = requests.Session()
    
    def rpc(self, endpoint, params):
        data = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": params,
            "id": 1
        }
        response = self.session.post(f"{self.url}{endpoint}", json=data)
        return response.json()

    def login(self):
        res = self.rpc("/web/session/authenticate", {"db": self.db, "login": self.user, "password": self.password})
        if 'error' in res:
             raise Exception(res['error'])
        self.uid = res['result']['uid']
        print(f"Logged in as UID: {self.uid}")

    def execute_kw(self, model, method, args=None, kwargs=None):
        if args is None: args = []
        if kwargs is None: kwargs = {}
        return self.rpc("/web/dataset/call_kw", {
            "model": model,
            "method": method,
            "args": args,
            "kwargs": kwargs
        })

def main():
    parser = argparse.ArgumentParser(description="Inspect Odoo Model Fields")
    parser.add_argument("--url", required=True, help="Odoo URL")
    parser.add_argument("--db", required=True, help="Database Name")
    parser.add_argument("--user", required=True, help="Username")
    parser.add_argument("--password", required=True, help="Password")
    parser.add_argument("--model", required=True, help="Model to inspect")
    
    args = parser.parse_args()
    
    client = OdooClient(args.url, args.db, args.user, args.password)
    try:
        client.login()
        
        print(f"Inspecting Model: {args.model}")
        res = client.execute_kw(args.model, 'fields_get', [], {'attributes': ['string', 'type', 'help']})
        
        if 'error' in res:
             print(f"Error: {res['error']}")
             sys.exit(1)
        
        fields = res['result']
        sorted_fields = sorted(fields.keys())
        print(f"Found {len(sorted_fields)} fields (showing matches for 'comp'):")
        for f in sorted_fields:
            if 'comp' in f.lower():
                print(f" - {f} ({fields[f]['type']})")

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    main()
