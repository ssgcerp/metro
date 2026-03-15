import requests
import json
import random
import logging
from datetime import datetime

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
            response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers, timeout=600)
            res_json = response.json()
            if 'error' in res_json:
                _logger.error(f"RPC ERROR: {res_json['error']}")
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
        return result.get('result')

def main():
    url = 'https://metro.equdaierp.com'
    db = 'newdb'
    username = 'admin'
    password = 'Amaze@321'
    end_date = '2025-12-31'

    client = OdooJsonRpcClient(url, db, username, password)
    if not client.authenticate():
        _logger.error("Authentication failed.")
        return

    _logger.info(f"Searching for all inbound customer payments until {end_date} across all companies...")

    # Find all inbound customer payments on or before end_date that are not in draft
    domain = [
        ('payment_type', '=', 'inbound'),
        ('partner_type', '=', 'customer'),
        ('state', '!=', 'draft'),
        ('date', '<=', end_date)
    ]
    
    # We use search instead of search_read first to avoid fetching too much data if there are thousands
    payment_ids = client.execute_kw('account.payment', 'search', [domain], {'order': 'date asc'})
    
    if not payment_ids:
        _logger.info("No payments found matching the criteria.")
        return

    _logger.info(f"Found {len(payment_ids)} payments to reset to draft.")

    # Process in batches of 100 for searching details
    batch_size = 100
    for i in range(0, len(payment_ids), batch_size):
        current_batch_ids = payment_ids[i:i + batch_size]
        payments = client.execute_kw('account.payment', 'read', [current_batch_ids, ['id', 'name', 'state', 'move_id', 'company_id', 'date']])
        
        for pay in payments:
            pay_id = pay['id']
            pay_name = pay['name']
            pay_date = pay['date']
            company_name = pay['company_id'][1] if pay.get('company_id') else "Unknown"
            move_id = pay['move_id'][0] if pay.get('move_id') else False

            _logger.info(f"[{company_name}] [{pay_date}] Resetting {pay_name} (ID: {pay_id}) to Draft...")
            
            try:
                # 1. Unreconcile associated move lines if posted
                if move_id:
                    lines = client.execute_kw('account.move.line', 'search', [[('move_id', '=', move_id), ('reconciled', '=', True)]])
                    if lines:
                        _logger.info(f"  Unreconciling lines for {pay_name}...")
                        client.execute_kw('account.move.line', 'remove_move_reconcile', [lines])

                # 2. Reset to draft
                client.execute_kw('account.payment', 'action_draft', [[pay_id]])
                _logger.info(f"  Successfully reset {pay_name} to Draft.")
            except Exception as e:
                _logger.error(f"  Failed for {pay_name}: {e}")

    _logger.info("Drafting process finished.")

if __name__ == "__main__":
    main()
