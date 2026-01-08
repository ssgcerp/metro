import requests
import json
import argparse
import logging
import sys
import time

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
            "id": 1,
        }
        headers = {"Content-Type": "application/json"}
        try:
            response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers, timeout=300)
            res_json = response.json()
            if 'error' in res_json:
                # _logger.error(f"RPC ERROR: {res_json['error']}")
                pass 
            return res_json
        except Exception as e:
            _logger.error(f"RPC EXCEPTION: {e}")
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
    parser = argparse.ArgumentParser(description='Reset and Cancel Customer Payments')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Odoo URL')
    parser.add_argument('--db', default='metrodb', help='Database name')
    parser.add_argument('--user', default='admin', help='Username')
    parser.add_argument('--password', default='Amaze@321', help='Password')
    parser.add_argument('--limit', type=int, default=200, help='Batch size')
    parser.add_argument('--company', help='Company Name or ID to filter by')
    
    args = parser.parse_args()

    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    
    if not client.authenticate():
        _logger.error("Authentication failed")
        sys.exit(1)

    # 0. Setup Multi-Company Context
    all_companies = client.execute_kw('res.company', 'search', [[]])
    if not all_companies:
        all_companies = [1]
    
    context = {'allowed_company_ids': all_companies}
    _logger.info(f"Using allowed_company_ids: {all_companies}")

    company_id = False
    if args.company:
        _logger.info(f"Looking up company: {args.company}")
        try:
             company_id = int(args.company)
             _logger.info(f"Using Company ID: {company_id}")
        except ValueError:
             # Fix 1: Properly pass kwargs
             kw = {'fields': ['id', 'name'], 'limit': 1, 'context': context}
             companies = client.execute_kw('res.company', 'search_read', 
                [[('name', 'ilike', args.company)]], 
                kwargs=kw
             )
             if companies:
                 company_id = companies[0]['id']
                 _logger.info(f"Found Company '{companies[0]['name']}' (ID: {company_id})")
             else:
                 _logger.error(f"Company '{args.company}' not found.")
                 sys.exit(1)

    while True:
        # Search for Payments (Draft, Posted, Sent, Paid, In Process)
        domain = [
            ('partner_type', '=', 'customer'),
            ('state', 'in', ['posted', 'sent', 'draft', 'paid', 'in_process'])
        ]
        
        if company_id:
            domain.append(('company_id', '=', company_id))
        
        _logger.info(f"Searching for payments to cancel (Limit: {args.limit})...")
        
        try:
            # Fix 2: Merge limit and context into a single kwargs dict
            search_kwargs = {'limit': args.limit, 'context': context}
            
            payment_ids = client.execute_kw(
                'account.payment', 
                'search', 
                [domain], 
                kwargs=search_kwargs
            )
        except Exception as e:
            _logger.error(f"Search failed: {e}")
            break

        if not payment_ids:
            _logger.info("No more payments found.")
            break
            
        _logger.info(f"Found {len(payment_ids)} payments. Processing...")
        
        success_count = 0
        
        # Output progress
        # Fix 3: Read with proper kwargs
        read_kwargs = {'fields': ['id', 'move_id', 'state', 'name'], 'context': context}
        payments_data = client.execute_kw('account.payment', 'read', [payment_ids], kwargs=read_kwargs)
        
        for pay in payments_data:
            pay_id = pay['id']
            move_id = pay['move_id'][0] if pay['move_id'] else False
            
            try:
                # 1. Unreconcile if Move exists
                if move_id:
                    # Find all lines of this move that are reconciled
                    lines = client.execute_kw('account.move.line', 'search', [[('move_id', '=', move_id)]], kwargs={'context': context})
                    if lines:
                        try:
                           client.execute_kw('account.move.line', 'remove_move_reconcile', [lines], kwargs={'context': context})
                        except Exception:
                           pass

                # 2. Reset to Draft
                if pay['state'] != 'draft':
                    client.execute_kw('account.payment', 'action_draft', [[pay_id]], kwargs={'context': context})
                
                # 3. Cancel
                # Often action_cancel raises if there are linked journal items that are reconciled, 
                # but we tried to unreconcile above.
                client.execute_kw('account.payment', 'action_cancel', [[pay_id]], kwargs={'context': context})
                
                success_count += 1
                if success_count % 10 == 0:
                    _logger.info(f"Processed {success_count}/{len(payment_ids)} in current batch...")
            except Exception as e:
                _logger.error(f"Failed to cancel payment {pay.get('name')} (ID {pay_id}): {e}")
                
        _logger.info(f"Batch complete. Successfully cancelled {success_count}/{len(payment_ids)} payments.")
        time.sleep(1)

if __name__ == '__main__':
    main()
