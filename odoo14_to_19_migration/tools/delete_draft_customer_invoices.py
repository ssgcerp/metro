import json
import random
import sys
import time
import requests
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
        
        response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers)
        
        try:
            result = response.json()
        except Exception as e:
            _logger.error(f"Failed to parse JSON response: {response.text}")
            raise e
            
        if 'error' in result:
            _logger.error(f"RPC Error: {result['error']}")
            # return {'error': result['error']}
            # Raise error to catch it
            raise Exception(result['error'])
        
        if 'result' not in result:
             return None
            
        return result['result']

    def authenticate(self):
        _logger.info("Authenticating...")
        params = {
            "db": self.db,
            "login": self.username,
            "password": self.password,
        }
        result = self.json_rpc("/web/session/authenticate", params)
        if result and 'uid' in result:
            self.uid = result['uid']
            _logger.info(f"Authenticated as user ID: {self.uid}")
            return True
        elif isinstance(result, dict) and 'error' in result:
            _logger.error(f"Authentication Error: {result['error']}")
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
    parser = argparse.ArgumentParser(description='Delete Draft Customer Invoices')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Odoo URL')
    parser.add_argument('--db', default='metrodb', help='Database name')
    parser.add_argument('--user', default='admin', help='Username')
    parser.add_argument('--password', default='Amaze@321', help='Password')
    parser.add_argument('--limit', type=int, default=100, help='Batch size')
    
    args = parser.parse_args()

    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    
    try:
        if not client.authenticate():
            _logger.error("Authentication failed")
            sys.exit(1)
    except Exception as e:
        _logger.error(f"Connection failed: {e}")
        sys.exit(1)

    while True:
        # Search for Draft Customer Invoices
        domain = [
            ('move_type', '=', 'out_invoice'), 
            ('state', '=', 'draft')
        ]
        
        _logger.info(f"Searching for draft customer invoices (Limit: {args.limit})...")
        
        invoice_ids = client.execute_kw(
            'account.move', 
            'search', 
            [domain], 
            {'limit': args.limit}
        )

        if not invoice_ids:
            _logger.info("No more draft customer invoices found.")
            break
            
        _logger.info(f"Found {len(invoice_ids)} draft invoices. Deleting...")
        
        # Delete
        count = 0
        try:
            # Try efficient batch unlink first
            client.execute_kw('account.move', 'unlink', [invoice_ids])
            count = len(invoice_ids)
            _logger.info(f"Batch deleted {count} invoices.")
        except Exception as e:
            _logger.warning(f"Batch delete failed ({str(e)}), trying one by one...")
            # Fallback to one by one
            for inv_id in invoice_ids:
                try:
                    client.execute_kw('account.move', 'unlink', [[inv_id]])
                    count += 1
                except Exception as inner_e:
                    _logger.error(f"Failed to delete invoice {inv_id}: {inner_e}")
        
        _logger.info(f"Deleted {count}/{len(invoice_ids)} in this pass.")
        time.sleep(1)

if __name__ == '__main__':
    main()
