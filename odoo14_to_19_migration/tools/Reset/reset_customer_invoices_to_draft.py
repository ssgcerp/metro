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
            # raise Exception(result['error']) # Don't raise, let caller handle
            return {'error': result['error']}
        
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
    parser = argparse.ArgumentParser(description='Reset Posted Customer Invoices to Draft')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Odoo URL')
    parser.add_argument('--db', default='newdb', help='Database name')
    parser.add_argument('--user', default='admin', help='Username')
    parser.add_argument('--password', default='Amaze@321', help='Password')
    parser.add_argument('--limit', type=int, default=100, help='Batch size')
    parser.add_argument('--company', default='6', help='Company Name or ID to filter by')
    
    args = parser.parse_args()
    
    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    
    if not client.authenticate():
        _logger.error("Authentication failed")
        sys.exit(1)

    company_id = False
    if args.company:
        _logger.info(f"Looking up company: {args.company}")
        try:
             # Try ID first
             company_id = int(args.company)
             _logger.info(f"Using Company ID: {company_id}")
        except ValueError:
             # Search by Name
             companies = client.execute_kw('res.company', 'search_read', [[('name', 'ilike', args.company)]], {'fields': ['id', 'name'], 'limit': 1})
             if companies:
                 company_id = companies[0]['id']
                 _logger.info(f"Found Company '{companies[0]['name']}' (ID: {company_id})")
             else:
                 _logger.error(f"Company '{args.company}' not found.")
                 sys.exit(1)

    while True:
        # Search for Posted Customer Invoices
        domain = [
            ('move_type', '=', 'out_invoice'), 
            ('state', '=', 'posted')
        ]
        
        if company_id:
            domain.append(('company_id', '=', company_id))
        
        _logger.info(f"Searching for posted customer invoices (Limit: {args.limit}, Company: {args.company if args.company else 'ALL'})...")
        
        invoice_ids = client.execute_kw(
            'account.move', 
            'search', 
            [domain], 
            {'limit': args.limit}
        )

        if not invoice_ids:
            _logger.info("No more posted customer invoices found.")
            break
            
        _logger.info(f"Found {len(invoice_ids)} invoices. Resetting to draft...")
        
        # Reset specific invoices to draft
        # Doing it one by one or in small batches is safer if errors occur
        success_count = 0
        for inv_id in invoice_ids:
            try:
                # 1. Attempt reset
                client.execute_kw('account.move', 'button_draft', [[inv_id]])
                success_count += 1
                if success_count % 10 == 0:
                    _logger.info(f"Reset {success_count}/{len(invoice_ids)} in current batch...")
            except Exception as e:
                _logger.error(f"Failed to reset invoice ID {inv_id}: {e}")
                
        _logger.info(f"Batch complete. Successfully reset {success_count}/{len(invoice_ids)} invoices.")
        time.sleep(1) # Brief pause between batches

if __name__ == '__main__':
    main()
