import requests
import json
import random
import logging

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

    client = OdooJsonRpcClient(url, db, username, password)
    if not client.authenticate():
        _logger.error("Authentication failed.")
        return

    processed_count = 0
    while True:
        # Find payments that are not in draft
        domain = [
            ('payment_type', '=', 'inbound'),
            ('partner_type', '=', 'customer'),
            ('state', '!=', 'draft')
        ]
        
        # We process 100 at a time and re-search (since they move out of state '!= draft')
        payment_ids = client.execute_kw('account.payment', 'search', [domain], {'limit': 100, 'order': 'id desc'})
        
        if not payment_ids:
            break

        _logger.info(f"Processing batch of {len(payment_ids)} payments (Total processed so far: {processed_count})...")
        payments = client.execute_kw('account.payment', 'read', [payment_ids, ['id', 'name', 'state', 'move_id', 'company_id', 'date']])
        
        for pay in payments:
            pay_id = pay['id']
            pay_name = pay['name']
            
            try:
                # 1. Unreconcile if move exists
                move_id = pay['move_id'][0] if pay.get('move_id') else False
                if move_id:
                    lines = client.execute_kw('account.move.line', 'search', [[('move_id', '=', move_id), ('reconciled', '=', True)]])
                    if lines:
                        client.execute_kw('account.move.line', 'remove_move_reconcile', [lines])

                # 2. Reset to draft
                client.execute_kw('account.payment', 'action_draft', [[pay_id]])
                processed_count += 1
            except Exception as e:
                _logger.error(f"  Failed for {pay_name} (ID: {pay_id}): {e}")
        
        _logger.info(f"  Finished batch of {len(payment_ids)}. Total reset so far: {processed_count}")

    _logger.info(f"Drafting process finished. Total reset: {processed_count}")

    _logger.info("Drafting process finished.")

if __name__ == "__main__":
    main()
