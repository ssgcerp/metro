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
        
        headers = {
            "Content-Type": "application/json",
        }
        
        try:
            response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers, timeout=300)
            result = response.json()
        except Exception as e:
            return None
            
        if 'error' in result:
            _logger.error(f"RPC Error: {result['error']}")
            return None
        
        if 'result' not in result:
             return None
            
        return result['result']

    def authenticate(self):
        params = {
            "db": self.db,
            "login": self.username,
            "password": self.password,
        }
        result = self.json_rpc("/web/session/authenticate", params)
        if result and 'uid' in result:
            self.uid = result['uid']
            return True
        return False

    def execute_kw(self, model, method, args=None, kwargs=None):
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        
        params = {
            "model": model,
            "method": method,
            "args": args,
            "kwargs": kwargs,
        }
        return self.json_rpc("/web/dataset/call_kw", params)

def main():
    parser = argparse.ArgumentParser(description='Remove Invoice Lines for Fallback Invoices')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Odoo URL')
    parser.add_argument('--db', default='metrodb', help='Database name')
    parser.add_argument('--user', default='admin', help='Username')
    parser.add_argument('--password', default='Amaze@321', help='Password')
    
    args = parser.parse_args()

    print("\n" + "="*80)
    print(f"CLEANUP TOOL: REMOVING ALL PRODUCTS FROM TARGET INVOICES")
    print("="*80)

    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    
    if not client.authenticate():
        print("Authentication failed")
        sys.exit(1)

    # 1. Search for invoices with fallback products
    fallback_codes = ['MIG_W_FALLBACK', 'MIGRATION_FALLBACK']
    domain = [
        ('odoo19_invoice_id.invoice_line_ids.product_id.default_code', 'in', fallback_codes),
        ('status', 'in', ['migrated', 'error', 'partial', 'queued']) 
    ]
    
    # We fetch IDs of migration lines
    print("Searching for invoices to clean...")
    mig_line_ids = client.execute_kw('customer.invoice.migration.line', 'search', [domain])
    
    if not mig_line_ids:
        print("No invoices found with fallback products to clean.")
        return

    print(f"Found {len(mig_line_ids)} invoices. Starting cleanup...")
    
    count = 0
    total = len(mig_line_ids)
    
    for mig_id in mig_line_ids:
        try:
            # Get Odoo 19 Invoice ID
            data = client.execute_kw('customer.invoice.migration.line', 'read', [[mig_id], ['uploaded_invoice_number', 'odoo19_invoice_id']])
            if not data: continue
            
            rec = data[0]
            inv_num = rec.get('uploaded_invoice_number') or 'Unknown'
            inv_19_id_raw = rec.get('odoo19_invoice_id')
            
            if inv_19_id_raw:
                inv_id = inv_19_id_raw[0] if isinstance(inv_19_id_raw, list) else inv_19_id_raw
                
                # Check state
                fields = client.execute_kw('account.move', 'read', [[inv_id], ['state']])
                if fields and fields[0]['state'] == 'posted':
                     # Must revert to draft first
                     try:
                         client.execute_kw('account.move', 'button_draft', [[inv_id]])
                     except Exception as e:
                         print(f"Failed to reset {inv_num} to draft: {e}")
                         continue
                
                # COMMAND: (5, 0, 0) - Delete all lines in the One2many field
                client.execute_kw('account.move', 'write', [[inv_id], {'invoice_line_ids': [(5, 0, 0)]}])
                
                count += 1
                if count % 10 == 0:
                     print(f"Cleared {count}/{total} invoices... (Last: {inv_num})")
            else:
                print(f"Skipping {inv_num}: No Odoo 19 Invoice linked.")

        except KeyboardInterrupt:
            print("\nStopped by user.")
            sys.exit(0)
        except Exception as e:
            print(f"Error processing {mig_id}: {e}")
            time.sleep(1)
        
    print(f"\nCleanup Finished. {count} invoices cleared.")

if __name__ == '__main__':
    main()
