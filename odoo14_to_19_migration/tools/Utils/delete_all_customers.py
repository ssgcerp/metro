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
                print(f"\nRPC ERROR: {res_json['error']}\n")
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
        if result and 'error' in result:
             raise Exception(result['error']['data']['message'] if 'data' in result['error'] else result['error']['message'])
        return result.get('result')

def main():
    parser = argparse.ArgumentParser(description='Delete All Customers in Odoo 19')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Odoo 19 URL')
    parser.add_argument('--db', default='newdb', help='Odoo 19 DB')
    parser.add_argument('--user', default='admin', help='Odoo 19 User')
    parser.add_argument('--password', default='Amaze@321', help='Odoo 19 Password')
    
    args = parser.parse_args()

    print("\n" + "="*80)
    print(f"DELETING ALL CUSTOMERS (PARTNERS)")
    print("="*80)

    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    
    if not client.authenticate():
        print("Authentication failed to Odoo 19!")
        sys.exit(1)

    print("Connected to Odoo 19.")

    print("Searching for customers/partners to delete...")
    try:
        # Search all partners except system ones (ID <= 10 usually covers Admin, Public User, Default Company, etc.)
        domain = [('active', 'in', [True, False]), ('id', '>', 10)]
        customer_ids = client.execute_kw('res.partner', 'search', [domain])
        
        if not customer_ids:
            print("No customers found.")
            sys.exit(0)
            
        print(f"Found {len(customer_ids)} customers. Attempting to delete...")
        
        chunk_size = 100
        deleted_count = 0
        archived_count = 0
        failed_count = 0
        
        for i in range(0, len(customer_ids), chunk_size):
            batch = customer_ids[i:i + chunk_size]
            print(f"Processing batch {i//chunk_size + 1} ({len(batch)} records)...")
            try:
                # Try batch unlink first
                client.execute_kw('res.partner', 'unlink', [batch])
                deleted_count += len(batch)
                print(f"  Successfully deleted batch.")
            except Exception as e:
                print(f"  Batch unlink failed, dropping to individual processing (Constraint likely)...")
                # Fallback to individual
                for cust_id in batch:
                    try:
                        client.execute_kw('res.partner', 'unlink', [[cust_id]])
                        deleted_count += 1
                    except Exception as e2:
                        try:
                            # Archive if deletion fails
                            client.execute_kw('res.partner', 'write', [[cust_id], {'active': False}])
                            archived_count += 1
                        except Exception as e3:
                            failed_count += 1

        print("\n" + "="*80)
        print("Deletion/Archiving Complete.")
        print(f"Deleted : {deleted_count}")
        print(f"Archived: {archived_count} (Could not delete due to dependencies)")
        print(f"Failed  : {failed_count}")
        print("="*80)
        
    except Exception as e:
        print(f"Error executing operation: {e}")

if __name__ == '__main__':
    main()
