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
            raise Exception(result['error'])
        
        if 'result' not in result:
             # Some void methods return None which might be missing 'result' in strict JSON-RPC but Odoo usually sends null
             _logger.warning(f"Response missing 'result': {result}")
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
        if result:
            self.uid = result['uid']
            _logger.info(f"Authenticated as user ID: {self.uid}")
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
    parser = argparse.ArgumentParser(description='Update Migrated Customer Invoices')
    parser.add_argument('--limit', type=int, default=50, help='Number of invoices to process per run')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Odoo URL')
    parser.add_argument('--db', default='metrodb', help='metrodb')
    parser.add_argument('--user', default='admin', help='admin')
    parser.add_argument('--password', default='Amaze@321', help='Amaze@321')
    parser.add_argument('--invoice', help='Specific invoice number to update (optional)')
    
    args = parser.parse_args()

    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    
    if not client.authenticate():
        _logger.error("Authentication failed")
        sys.exit(1)

    # Search for invoices to update
    # We look for 'customer.invoice.migration.line' records in various statuses
    # User requested to "execute whatever in queued"
    domain = [('status', 'in', ['migrated', 'already_migrated', 'queued'])]
    
    if args.invoice:
        domain = [('uploaded_invoice_number', '=', args.invoice)] # Override status check if specific invoice
        _logger.info(f"Searching for specific invoice: {args.invoice}")
    else:
        _logger.info(f"Searching for latest {args.limit} invoices (migrated, already_migrated, queued)...")

    # Fetch migration lines
    migration_line_ids = client.execute_kw(
        'customer.invoice.migration.line', 
        'search', 
        [domain], 
        {'limit': args.limit, 'order': 'id desc'}
    )

    if not migration_line_ids:
        _logger.info("No migrated invoices found to update.")
        return

    _logger.info(f"Found {len(migration_line_ids)} invoices to update. Starting update process...")

    # Create the wizard record
    wizard_id = client.execute_kw(
        'customer.invoice.updater',
        'create',
        [{
            'migration_line_ids': [[6, 0, migration_line_ids]]
        }]
    )
    
    if not wizard_id:
        _logger.error("Failed to create update wizard.")
        sys.exit(1)
        
    _logger.info(f"Created updater wizard ID: {wizard_id}")

    # Trigger the update action
    try:
        # Note: wizard_id is an integer (ID), but call_kw for instance methods expects list of IDs in args[0]
        client.execute_kw(
            'customer.invoice.updater',
            'action_update_invoices',
            [[wizard_id]]
        )
        _logger.info("✅ Update action completed successfully provided no exceptions were raised.")
    except Exception as e:
        _logger.error(f"❌ Error during update execution: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
