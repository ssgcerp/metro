import requests
import json
import random

def rpc(url, model, method, args=None, kwargs=None):
    if args is None: args = []
    if kwargs is None: kwargs = {}
    data = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"model": model, "method": method, "args": args, "kwargs": kwargs},
        "id": random.randint(0, 1000000000),
    }
    return requests.post(f"{url}/web/dataset/call_kw", json=data).json().get('result')

url = 'https://metro.equdaierp.com'
db = 'newdb'
user = 'admin'
pw = 'Amaze@321'

auth = requests.post(f"{url}/web/session/authenticate", json={"jsonrpc":"2.0","method":"call","params":{"db":db,"login":user,"password":pw}}).json()
uid = auth['result']['uid']

comp_id = rpc(url, 'res.company', 'search', [[('name', '=', 'ABU DHABI')]], {'limit': 1})[0]
total = rpc(url, 'account.payment', 'search_count', [[('company_id', '=', comp_id)]])
draft = rpc(url, 'account.payment', 'search_count', [[('company_id', '=', comp_id), ('state', '=', 'draft')]])
posted = rpc(url, 'account.payment', 'search_count', [[('company_id', '=', comp_id), ('state', '=', 'posted')]])

print(f"AUH Payments - Total: {total}, Draft: {draft}, Posted/Other: {total-draft}")
