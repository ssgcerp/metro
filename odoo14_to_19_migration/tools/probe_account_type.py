import json
import requests

def main():
    dest_url = 'http://localhost:8079'
    dest_db = 'metrodb'
    dest_user = 'admin'
    dest_password = 'Amaze@321'
    
    session = requests.Session()
    session.post(f"{dest_url}/web/session/authenticate", json={
        "jsonrpc": "2.0", "method": "call", "params": {"db": dest_db, "login": dest_user, "password": dest_password}, "id": 1
    })

    # Get Field Selection
    params = {
        "model": "account.account",
        "method": "fields_get",
        "args": [['account_type']],
        "kwargs": {"attributes": ["selection"]}
    }
    res = session.post(f"{dest_url}/web/dataset/call_kw", json={
        "jsonrpc": "2.0", "method": "call", "params": params, "id": 2
    }).json()
    
    if 'result' in res:
        field_info = res['result'].get('account_type', {})
        selection = field_info.get('selection', [])
        print("VALID ACCOUNT TYPES:")
        for code, label in selection:
            print(f" - {code}: {label}")
    else:
        print(f"Error: {res}")

if __name__ == '__main__':
    main()
