
import json
import random
import requests

def main():
    url = "http://localhost:8079/web/dataset/call_kw"
    db = "metrodb"
    username = "admin"
    password = "Amaze@321" 

    session = requests.Session()
    auth_url = "http://localhost:8079/web/session/authenticate"
    auth_data = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": db,
            "login": username,
            "password": password
        },
        "id": 1
    }
    
    try:
        res = session.post(auth_url, json=auth_data).json()
        if 'error' in res:
            print(f"Auth Error: {res['error']}")
            return
        
        # Check specifically for the bill we just saw created: BILL/2026/01/0002
        bill_ref = 'BILL/2026/01/0002'
        print(f"Searching for {bill_ref}...")
        
        # 1. Search by Name
        data = {
            "jsonrpc": "2.0", "method": "call",
            "params": {
                "model": "account.move", "method": "search_read",
                "args": [[('name', '=', bill_ref)]],
                "kwargs": {"fields": ['name', 'ref', 'company_id', 'move_type']}
            }, "id": 2
        }
        res = session.post(url, json=data).json()
        print(f"Search Results (Name={bill_ref}): {res.get('result')}")

        # 2. Search by Ref
        data['params']['args'] = [[('ref', '=', bill_ref)]]
        res = session.post(url, json=data).json()
        print(f"Search Results (Ref={bill_ref}): {res.get('result')}")

        # 3. Search All newly created IDs to see what happened to them
        # IDs seen in logs: 65866, 65785, 65697
        ids = [65866, 65785, 65697]
        data['params']['args'] = [[('id', 'in', ids)]]
        res = session.post(url, json=data).json()
        print(f"Specific IDs {ids}:")
        for r in res.get('result', []):
            print(r)

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    main()
