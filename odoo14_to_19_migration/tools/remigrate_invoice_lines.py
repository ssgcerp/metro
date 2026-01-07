import json
import random
import sys
import time
import requests
import argparse
import logging
import socket

# Increase default socket timeout
socket.setdefaulttimeout(300)

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
    parser = argparse.ArgumentParser(description='Re-Migrate Customer Invoice Lines')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Odoo URL')
    parser.add_argument('--db', default='metrodb', help='Database name')
    parser.add_argument('--user', default='admin', help='Username')
    parser.add_argument('--password', default='Amaze@321', help='Password')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of invoices to process (0 for all)')
    
    args = parser.parse_args()


    print("\n" + "="*110)
    print(f"{'Invoice':<10} | {'Processed':<9} | {'O14 Prods':<10} | {'O14 Total':<12} | {'Mig Prods':<10} | {'Mig Total':<12} | Status")
    print("="*110)

    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    
    if not client.authenticate():
        print("Authentication failed")
        sys.exit(1)

    # 1. Search (All migrated/partial/error)
    domain = [('status', 'in', ['migrated', 'partial', 'error'])]
    
    print("Searching for invoices...", end='\r')
    search_args = [domain]
    if args.limit > 0:
        mig_line_ids = client.execute_kw('customer.invoice.migration.line', 'search', search_args, {'limit': args.limit})
    else:
        mig_line_ids = client.execute_kw('customer.invoice.migration.line', 'search', search_args)
    
    if not mig_line_ids:
        print("\nNo invoices found.")
        return

    processed_count = 0
    total_count = len(mig_line_ids)
    
    for mig_id in mig_line_ids:
        try:
            # Get basic info
            data = client.execute_kw('customer.invoice.migration.line', 'read', [[mig_id], ['uploaded_invoice_number']])
            if not data: continue
            rec = data[0]
            inv_num = rec.get('uploaded_invoice_number', 'Unknown')
            
            # Execute Update (which now returns stats!)
            updater_id = client.execute_kw('customer.invoice.updater', 'create', [{'migration_line_ids': [[6, 0, [mig_id]]]}])
            if updater_id:
                uid = updater_id[0] if isinstance(updater_id, list) else updater_id
                
                # Action returns dict with stats: { 'o14_lines': X, 'o14_total': Y, 'o19_lines': Z, 'o19_total': W }
                result = client.execute_kw('customer.invoice.updater', 'action_update_invoices', [[uid]])
                
                processed_count += 1
                
                o14_cnt = '?'
                o14_tot = '?'
                o19_cnt = '?'
                o19_tot = '?'
                
                if isinstance(result, dict):
                    o14_cnt = result.get('o14_lines', 0)
                    o14_tot = f"{result.get('o14_total', 0.0):.2f}"
                    o19_cnt = result.get('o19_lines', 0)
                    o19_tot = f"{result.get('o19_total', 0.0):.2f}"
                
                status_icon = "✅ DONE"
                print(f"{inv_num:<10} | {processed_count}/{total_count:<6} | {o14_cnt:<10} | {o14_tot:<12} | {o19_cnt:<10} | {o19_tot:<12} | {status_icon}")
                
            else:
                 print(f"{inv_num:<10} | Failed to create wizard | Status: ❌ FAIL")

        except KeyboardInterrupt:
            print("\nStopped by user.")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            try: client.authenticate()
            except: pass
            time.sleep(1)
            
        time.sleep(0.05)

    print("\nRe-migration process finished.")

if __name__ == '__main__':
    main()
