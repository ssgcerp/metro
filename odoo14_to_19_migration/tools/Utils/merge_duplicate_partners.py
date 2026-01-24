import json
import random
import sys
import time
import requests
import argparse
import logging
import xmlrpc.client

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
        return result.get_result() if hasattr(result, 'get_result') else result.get('result')

def main():
    parser = argparse.ArgumentParser(description='Merge Duplicate Partners in Odoo 19')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Odoo 19 URL')
    parser.add_argument('--db', default='metrodb', help='Odoo 19 DB')
    parser.add_argument('--user', default='admin', help='Odoo 19 User')
    parser.add_argument('--password', default='Amaze@321', help='Odoo 19 Password')
    
    args = parser.parse_args()

    print("\n" + "="*80)
    print(f"MERGING DUPLICATE PARTNERS")
    print("="*80)

    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    
    if not client.authenticate():
        print("Authentication failed to Odoo 19!")
        sys.exit(1)

    print("Connected to Odoo 19.")

    # 1. Find Duplicates
    # Group by name
    print("Searching for duplicates...")
    # We can use read_group to find duplicates efficiently
    # But read_group in Odoo JSON-RPC needs careful syntax.
    # Group by name, count.
    
    # Alternatively, fetch all names and IDs and process locally (if < 100k partners, okay).
    # Let's try read_group first.
    
    try:
        # read_group(domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True)
        # args needs to be a list containing these arguments
        groups = client.execute_kw('res.partner', 'read_group', [
            [('active', '=', True)], # domain
            ['name'], # fields
            ['name']  # groupby
        ])
    except Exception as e:
        print(f"read_group failed: {e}")
        sys.exit(1)
        
    duplicates = [g for g in groups if g['name_count'] > 1 and g['name']]
    print(f"Found {len(duplicates)} names with duplicates.")
    
    processed_count = 0
    
    for g in duplicates:
        name = g['name']
        count = g['name_count']
        print(f"Processing '{name}' ({count} copies)...")
        
        # Fetch IDs for this name, ordered by ID asc
        # We need ALL IDs.
        ids = client.execute_kw('res.partner', 'search', [[('name', '=', name)]], {'order': 'id asc'})
        
        if not ids or len(ids) < 2:
            print(f"  Skipping (found {len(ids)} actual records).")
            continue
            
        dest_id = ids[0]
        source_ids = ids[1:]
        
        # Merge Logic
        # Odoo Limit: Cannot merge more than 3 contacts at once (Safety).
        # We must chunk the sources. (Dest + 2 Sources = 3).
        
        chunk_size = 2
        for i in range(0, len(source_ids), chunk_size):
            batch_sources = source_ids[i:i + chunk_size]
            partners_to_merge = [dest_id] + batch_sources
            
            try:
                # Create wizard
                wiz_vals = {
                    'state': 'option',
                    'partner_ids': [(6, 0, partners_to_merge)],
                    'dst_partner_id': dest_id,
                }
                wiz_id = client.execute_kw('base.partner.merge.automatic.wizard', 'create', [wiz_vals])
                
                # Call merge
                client.execute_kw('base.partner.merge.automatic.wizard', 'action_merge', [wiz_id])
                
                print(f"  Merged batch {i//chunk_size + 1}: {len(batch_sources)} partners into ID {dest_id}.")
                processed_count += 1
                
            except Exception as e:
                print(f"  Merge FAILED for batch in '{name}': {e}")
                # Analyze error
                if 'UserError' in str(e) and 'safety reasons' in str(e):
                    # Should be handled by chunk size, but if dest is somehow problematic?
                    pass

    print(f"\nFinished. Processed {processed_count} groups.")

if __name__ == '__main__':
    main()
