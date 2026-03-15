import pandas as pd
import requests
import json
import random

def json_rpc(url, method, params):
    data = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": params,
        "id": random.randint(0, 1000000000),
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, data=json.dumps(data), headers=headers, timeout=300)
        return response.json()
    except Exception as e:
        print(f"RPC EXCEPTION: {e}")
        return None

def authenticate(url, db, username, password):
    params = {"db": db, "login": username, "password": password}
    result = json_rpc(f"{url}/web/session/authenticate", "call", params)
    if result and 'result' in result and 'uid' in result['result']:
        return result['result']['uid']
    return None

def execute_kw(url, model, method, args=None, kwargs=None):
    if args is None: args = []
    if kwargs is None: kwargs = {}
    params = {"model": model, "method": method, "args": args, "kwargs": kwargs}
    result = json_rpc(f"{url}/web/dataset/call_kw", "call", params)
    return result.get('result')

def main():
    url = "https://metro.equdaierp.com"
    src_db = "metrodb"
    dest_db = "newdb"
    user = "admin"
    password = "Amaze@321"
    company_name = "ABU DHABI"

    src_uid = authenticate(url, src_db, user, password)
    dest_uid = authenticate(url, dest_db, user, password)

    if not src_uid or not dest_uid:
        print("Auth failed")
        return

    src_comp = execute_kw(url, 'res.company', 'search', [[('name', '=', company_name)]])
    if not src_comp:
        print("Source company not found")
        return
    src_comp_id = src_comp[0]

    dest_comp = execute_kw(url, 'res.company', 'search', [[('name', '=', company_name)]])
    if not dest_comp:
        print("Dest company not found")
        return
    dest_comp_id = dest_comp[0]

    domain = [
        ('payment_type', '=', 'inbound'),
        ('partner_type', '=', 'customer'),
        ('state', 'in', ['paid', 'in_process', 'draft']),
        ('company_id', '=', src_comp_id)
    ]

    print(f"Fetching source payments for {company_name}...")
    src_payments = []
    offset = 0
    limit = 1000
    while True:
        batch = execute_kw(url, 'account.payment', 'search_read', [domain], {'fields': ['name'], 'limit': limit, 'offset': offset})
        if not batch: break
        src_payments.extend([p['name'] for p in batch])
        offset += limit
        print(f"Fetched {len(src_payments)} so far...")

    print(f"Total source payments: {len(src_payments)}")

    print(f"Fetching dest payments for {company_name}...")
    dest_payments = set()
    offset = 0
    while True:
        batch = execute_kw(url, 'account.payment', 'search_read', [[('company_id', '=', dest_comp_id)]], {'fields': ['name'], 'limit': limit, 'offset': offset})
        if not batch: break
        dest_payments.update([p['name'] for p in batch])
        offset += limit
        print(f"Fetched {len(dest_payments)} so far...")

    missing = [p for p in src_payments if p not in dest_payments]
    print(f"Total missing: {len(missing)}")
    if missing:
        print("First 10 missing:")
        for m in missing[:10]:
            print(f" - {m}")

if __name__ == "__main__":
    main()
