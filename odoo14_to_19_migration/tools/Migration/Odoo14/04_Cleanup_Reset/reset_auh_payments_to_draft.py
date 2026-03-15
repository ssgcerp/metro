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
            response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers, timeout=300)
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
    company_name = 'ABU DHABI'

    client = OdooJsonRpcClient(url, db, username, password)
    if not client.authenticate():
        _logger.error("Authentication failed.")
        return

    # Find ABU DHABI company
    company_search = client.execute_kw('res.company', 'search', [[('name', '=', company_name)]], {'limit': 1})
    if not company_search:
        _logger.error(f"Company '{company_name}' not found.")
        return
    company_id = company_search[0]
    _logger.info(f"Found Company '{company_name}' ID: {company_id}")

    # Find all inbound customer payments for this company
    domain = [
        ('company_id', '=', company_id),
        ('payment_type', '=', 'inbound'),
        ('partner_type', '=', 'customer'),
        ('state', '!=', 'draft')
    ]
    
    payments = client.execute_kw('account.payment', 'search_read', [domain], {'fields': ['id', 'name', 'state', 'move_id']})
    
    if not payments:
        _logger.info("No posted/paid payments found for Abu Dhabi.")
        return

    _logger.info(f"Found {len(payments)} payments to reset to draft.")

    for pay in payments:
        pay_id = pay['id']
        pay_name = pay['name']
        move_id = pay['move_id'][0] if pay.get('move_id') else False

        _logger.info(f"Resetting {pay_name} (ID: {pay_id}) to Draft...")
        
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
