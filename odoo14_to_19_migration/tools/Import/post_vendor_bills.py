
import json
import random
import sys
import time
import requests
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
_logger = logging.getLogger(__name__)

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
            response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers, timeout=300)
            res_json = response.json()
            if 'error' in res_json:
                # print(f"\nRPC ERROR: {res_json['error']}\n")
                return res_json
            return res_json
        except Exception as e:
            print(f"RPC EXCEPTION: {e}")
            return None

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
        if hasattr(result, 'get_result'):
             return result.get_result()
        return result.get('result')

def main():
    parser = argparse.ArgumentParser(description='Post All Draft Vendor Bills in Odoo 19')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Odoo 19 URL')
    parser.add_argument('--db', default='metrodb', help='Odoo 19 DB')
    parser.add_argument('--user', default='admin', help='Odoo 19 User')
    parser.add_argument('--password', default='Amaze@321', help='Odoo 19 Password')
    
    args = parser.parse_args()

    print("\n" + "="*80)
    print(f"POSTING DRAFT VENDOR BILLS ON {args.url} ({args.db})")
    print("="*80)

    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    
    if not client.authenticate():
        print("Authentication failed to Odoo 19!")
        sys.exit(1)

    print("Connected to Odoo 19.")

    # Search for Draft Vendor Bills
    # move_type = 'in_invoice' (Vendor Bill)
    # state = 'draft'
    domain = [
        ('move_type', '=', 'in_invoice'),
        ('state', '=', 'draft')
    ]
    
    # Get IDs
    bill_ids = client.execute_kw('account.move', 'search', [domain])
    
    if not bill_ids:
        print("No Draft Vendor Bills found.")
        sys.exit(0)
        
    print(f"Found {len(bill_ids)} draft vendor bills. Starting posting process...")
    
    success_count = 0
    failure_count = 0
    
    for i, bill_id in enumerate(bill_ids):
        try:
            # We fetch name/ref for logging
            details = client.execute_kw('account.move', 'read', [[bill_id], ['name', 'ref', 'partner_id']])
            if details:
                name = details[0].get('name')
                ref = details[0].get('ref')
                partner = details[0].get('partner_id')[1] if details[0].get('partner_id') else 'Unknown'
                display_name = f"{name} ({ref}) - {partner}"
            else:
                display_name = f"ID {bill_id}"

            print(f"[{i+1}/{len(bill_ids)}] Posting {display_name}...", end=" ")
            
            # Call action_post
            # In Odoo, action_post usually returns True or a dict (action). If it errors, execute_kw might return None or the error dict.
            # Our client prints RPC ERROR if key exists.
            
            # We call it as a method on the record
            result = client.execute_kw('account.move', 'action_post', [[bill_id]])
            
            # Check if result indicates error (our client helper returns the full json if error key exists, or just result if success)
            # Actually our client execute_kw returns result.get('result') OR None if error?
            # Let's check print logic in client.json_rpc. It returns res_json.
            # execute_kw returns get_result() or result['result'].
            
            # If successful, usually returns True or None (void).
            # If RPC error, our execute_kw might receive None or we might have printed it in json_rpc.
            
            # Let's assume success if no exception raised, but we are printing errors in json_rpc.
            # We can verify state.
            
            # Check state
            post_check = client.execute_kw('account.move', 'read', [[bill_id], ['state']])
            if post_check and post_check[0]['state'] == 'posted':
                print("SUCCESS")
                success_count += 1
            else:
                print("FAILED (Not Posted)")
                failure_count += 1
                
        except Exception as e:
            print(f"EXCEPTION: {e}")
            failure_count += 1

    print("\n" + "="*80)
    print(f"FINISHED. Success: {success_count}, Failed: {failure_count}")
    print("="*80)

if __name__ == "__main__":
    main()
