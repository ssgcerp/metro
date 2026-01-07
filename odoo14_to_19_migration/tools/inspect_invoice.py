import logging
import requests
import json
import random

# Inline Odoo14APIClient for standalone usage
class Odoo14APIClient:
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
        response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers)
        result = response.json()
        if 'error' in result:
            return None
        return result.get('result')

    def authenticate(self):
        params = {"db": self.db, "login": self.username, "password": self.password}
        result = self.json_rpc("/web/session/authenticate", params)
        if result and 'uid' in result:
            self.uid = result['uid']
            return True
        return False

    def search_read(self, model, domain, fields, limit=0):
        return self.execute_kw(model, 'search_read', [domain, fields], {'limit': limit})
        
    def execute_kw(self, model, method, args=None, kwargs=None):
        if args is None: args = []
        if kwargs is None: kwargs = {}
        params = {"model": model, "method": method, "args": args, "kwargs": kwargs}
        return self.json_rpc("/web/dataset/call_kw", params)

# Configure logging
logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

# Hardcoded config from previous scripts
URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASSWORD = "Amaze@321"

def inspect_invoice(invoice_name):
    client = Odoo14APIClient(URL, DB, USER, PASSWORD)
    if not client.authenticate():
        print("Auth failed")
        return

    print(f"Searching for invoice {invoice_name}...")
    inv = client.search_read('account.move', [('name', '=', invoice_name)], ['id', 'name', 'invoice_line_ids'], limit=1)
    
    if not inv:
        print("Invoice not found")
        return

    inv_id = inv[0]['id']
    print(f"Found Invoice ID: {inv_id}")

    print("Fetching lines...")
    lines = client.search_read(
        'account.move.line', 
        [('move_id', '=', inv_id)], 
        ['id', 'name', 'product_id', 'quantity', 'price_unit', 'credit', 'debit', 'display_type'],
        limit=50
    )

    for l in lines:
        print(f"Line ID: {l['id']}")
        print(f"  Name: {l['name']}")
        print(f"  Product: {l['product_id']}") # [id, name]
        print(f"  Qty: {l['quantity']}")
        print(f"  Price: {l['price_unit']}")
        # print(f"  Exclude: {l['exclude_from_invoice_tab']}")
        print("-" * 20)

if __name__ == "__main__":
    # Based on screenshot, invoice number seems to be 15187 (or similar from list)
    # The screenshot shows "Due Date Dec 5 2025"... wait, the screenshot has "15187" in the list view.
    # The detail view doesn't show the number clearly but let's try 15187 or 15178 from the list.
    inspect_invoice("15178") # Trying one from the list in screenshot
