import json
import random
import sys
import requests
import argparse

def main():
    url = "https://metro.equdaierp.com"
    db = "metrodb"
    username = "admin"
    password = "Amaze@321"
    
    print(f"Connecting to {url}...")
    
    # JSON-RPC
    def json_rpc(endpoint, params):
        data = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": params,
            "id": random.randint(0, 1000000000),
        }
        try:
            response = requests.post(f"{url}{endpoint}", json=data)
            return response.json()
        except Exception as e:
            print(e)
            return {}

    # Authenticate
    auth = json_rpc("/web/session/authenticate", {"db": db, "login": username, "password": password})
    if not auth.get('result', {}).get('uid'):
        print("Auth failed")
        return
        
    uid = auth['result']['uid']
    print("Authenticated.")
    
    # Get Fields
    res = json_rpc("/web/dataset/call_kw", {
        "model": "account.payment",
        "method": "fields_get",
        "args": [],
        "kwargs": {"attributes": ["string", "type"]}
    })
    
    if 'result' in res:
        fields = res['result']
        print("\nFields on account.payment:")
        keys = sorted(fields.keys())
        for k in keys:
            if k in ['ref', 'memo', 'communication', 'name', 'reference']:
                print(f" -> {k}: {fields[k]}")
        
    else:
        print("Failed to get fields")
        print(res)

if __name__ == "__main__":
    main()
