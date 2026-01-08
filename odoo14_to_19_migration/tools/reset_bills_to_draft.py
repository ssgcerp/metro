import requests
import json
import argparse
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

class OdooClient:
    def __init__(self, url, db, username, password):
        self.url = url
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
            "id": 1
        }
        headers = {'Content-Type': 'application/json'}
        response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers)
        
        try:
            result = response.json()
        except Exception:
            _logger.error(f"Invalid JSON response: {response.text}")
            raise

        if 'error' in result:
            raise Exception(result['error'])
        
        if 'result' not in result:
            _logger.error(f"Unexpected JSON-RPC response format (missing 'result' and 'error'): {result}")
            raise Exception(f"Invalid RPC response: {result}")
            
        return result['result']

    def authenticate(self):
        _logger.info("Authenticating...")
        result = self.json_rpc('/web/session/authenticate', {
            'db': self.db,
            'login': self.username,
            'password': self.password
        })
        if result.get('uid'):
            self.uid = result['uid']
            _logger.info(f"Authenticated as user ID: {self.uid}")
            return True
        return False

    def execute_kw(self, model, method, args, kwargs=None):
        if not kwargs:
            kwargs = {}
        return self.json_rpc('/web/dataset/call_kw', {
            'model': model,
            'method': method,
            'args': args,
            'kwargs': kwargs
        })

def reset_bills_to_draft(url, db, username, password):
    client = OdooClient(url, db, username, password)
    
    try:
        if not client.authenticate():
            _logger.error("Authentication failed.")
            return

        # 1. Search for Posted Vendor Bills
        _logger.info("Searching for Posted Vendor Bills...")
        bill_ids = client.execute_kw('account.move', 'search', [[
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted')
        ]])
        
        if not bill_ids:
            _logger.info("No posted vendor bills found.")
            return

        _logger.info(f"Found {len(bill_ids)} posted vendor bills. Processing...")

        # 2. Reset in batches
        BATCH_SIZE = 10  # Reduced batch size for better error handling
        total_reset = 0
        
        for i in range(0, len(bill_ids), BATCH_SIZE):
            batch_ids = bill_ids[i:i + BATCH_SIZE]
            try:
                # Attempt reset
                client.execute_kw('account.move', 'button_draft', [batch_ids])
                total_reset += len(batch_ids)
                _logger.info(f"Progress: {total_reset}/{len(bill_ids)} bills reset to draft.")
            except Exception as e:
                error_msg = str(e)
                if "due date" in error_msg.lower() and "payable account" in error_msg.lower():
                    _logger.warning(f"Batch {i} failed with Due Date error. Attempting to fix lines and retry...")
                    _fix_due_dates(client, batch_ids)
                    try:
                        client.execute_kw('account.move', 'button_draft', [batch_ids])
                        total_reset += len(batch_ids)
                        _logger.info(f"Progress: {total_reset}/{len(bill_ids)} bills reset to draft (after fix).")
                    except Exception as retry_e:
                         _logger.error(f"Failed to reset batch {i} even after fix: {str(retry_e)}")
                else:
                    _logger.error(f"Error processing batch starting at index {i}: {str(e)}")

        _logger.info("Done! Process complete.")
        
    except Exception as e:
        _logger.error(f"An error occurred: {str(e)}")

def _fix_due_dates(client, move_ids):
    """
    Fixes the 'Any journal item on a payable account must have a due date and vice versa' error.
    1. Sets date_maturity on payable/receivable lines if missing.
    2. Removes date_maturity from other lines if present.
    """
    if not move_ids:
        return

    try:
        # Fetch lines for these moves
        # We need: id, account_id, date_maturity, move_id(date)
        lines = client.execute_kw('account.move.line', 'search_read', [
            [('move_id', 'in', move_ids)]
        ], {'fields': ['id', 'account_id', 'date_maturity', 'move_id']})
        
        if not lines:
            return

        # Fetch account types to identify payable/receivable
        account_ids = list(set(l['account_id'][0] for l in lines if l.get('account_id')))
        accounts = client.execute_kw('account.account', 'search_read', [
            [('id', 'in', account_ids)]
        ], {'fields': ['id', 'account_type']})
        
        payable_account_ids = {
            a['id'] for a in accounts 
            if a.get('account_type') in ['asset_receivable', 'liability_payable']
        }
        
        # Get move dates for fallback
        moves = client.execute_kw('account.move', 'search_read', [
            [('id', 'in', move_ids)]
        ], {'fields': ['id', 'date', 'invoice_date']})
        move_dates = {m['id']: (m.get('invoice_date') or m.get('date')) for m in moves}

        for line in lines:
            line_id = line['id']
            acc_id = line['account_id'][0] if line.get('account_id') else False
            date_maturity = line.get('date_maturity')
            move_id = line['move_id'][0]
            
            is_payable = acc_id in payable_account_ids
            
            # Case 1: Payable/Receivable line BUT missing due date -> FIX: Set to move date
            if is_payable and not date_maturity:
                fix_date = move_dates.get(move_id)
                if fix_date:
                    _logger.info(f"Fixing missing due date for line {line_id} (Move {move_id}) -> {fix_date}")
                    client.execute_kw('account.move.line', 'write', [[line_id], {'date_maturity': fix_date}])
            
            # Case 2: NOT Payable/Receivable line BUT has due date -> FIX: Remove it
            elif not is_payable and date_maturity:
                _logger.info(f"Removing invalid due date for line {line_id} (Move {move_id})")
                client.execute_kw('account.move.line', 'write', [[line_id], {'date_maturity': False}])

    except Exception as e:
        _logger.error(f"Error during line fix: {str(e)}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Reset Posted Vendor Bills to Draft')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Odoo URL (default: http://localhost:8079)')
    parser.add_argument('--db', default='metrodb', help='Database name (default: metrodb)')
    parser.add_argument('--user', default='admin', help='Username (default: admin)')
    parser.add_argument('--password', default='Amaze@321', help='Password (default: Amaze@321)')
    
    args = parser.parse_args()
    
    print(f"Connecting to {args.url} / {args.db} as {args.user}")
    reset_bills_to_draft(args.url, args.db, args.user, args.password)
