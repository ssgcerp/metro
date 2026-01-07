import json
import random
import requests
import argparse

def main():
    dest_url = 'http://localhost:8079'
    dest_db = 'metrodb'
    dest_user = 'admin'
    dest_password = 'Amaze@321'
    
    auth_params = {"db": dest_db, "login": dest_user, "password": dest_password}
    session = requests.Session()
    
    # Auth
    res = session.post(f"{dest_url}/web/session/authenticate", json={
        "jsonrpc": "2.0", "method": "call", "params": auth_params, "id": 1
    }).json()
    
    if 'result' not in res:
        print("Auth failed")
        return

    # Get Fields
    params = {
        "model": "account.account",
        "method": "fields_get",
        "args": [],
        "kwargs": {"attributes": ["string", "type", "relation"]}
    }
    res = session.post(f"{dest_url}/web/dataset/call_kw", json={
        "jsonrpc": "2.0", "method": "call", "params": params, "id": 2
    }).json()
    
    fields = res.get('result', {})
    print("FIELDS FOUND:")
    if 'company_id' in fields: print(f" - company_id: {fields['company_id']}")
    if 'company_ids' in fields: print(f" - company_ids: {fields['company_ids']}")
    if 'account_type' in fields: print(f" - account_type: {fields['account_type']}")
    if 'user_type_id' in fields: print(f" - user_type_id: {fields['user_type_id']}")

if __name__ == '__main__':
    main()
