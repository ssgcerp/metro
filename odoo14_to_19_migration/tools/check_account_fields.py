import json
import random
import sys
import requests
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

session = requests.Session()

def json_rpc(url, method, params):
    data = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": params,
        "id": random.randint(0, 1000000000),
    }
    response = session.post(url, json=data)
    return response.json()

def main():
    url = "http://localhost:8079/web/dataset/call_kw"
    auth_url = "http://localhost:8079/web/session/authenticate"
    db = "metrodb"
    user = "admin"
    password = "admin" # Trying default first, update if needed

    # Authenticate
    auth_params = {"db": db, "login": user, "password": password}
    auth_result = json_rpc(auth_url, "call", auth_params)
    
    if 'error' in auth_result:
        # Try the other password
        auth_params['password'] = "Amaze@321"
        auth_result = json_rpc(auth_url, "call", auth_params)
        
    if 'result' not in auth_result:
        print("Auth failed", auth_result)
        return

    uid = auth_result['result']['uid']
    print(f"Authenticated as {uid}")

    # Fetch fields of account.account
    params = {
        "model": "account.account",
        "method": "fields_get",
        "args": [],
        "kwargs": {"attributes": ["string", "type", "required"]},
    }
    
    result = json_rpc(url, "call", params)
    
    if 'result' in result:
        fields = result['result']
        print("Fields of account.account:")
        if 'company_id' in fields:
            print(f"  company_id: {fields['company_id']}")
        else:
            print("  company_id: NOT FOUND")
            
        # Check for company related fields
        for f in fields:
            if 'company' in f:
                print(f"  * {f}: {fields[f]}")
    else:
        print("Error fetching fields:", result)

if __name__ == "__main__":
    main()
