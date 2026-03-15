import json
import random
import requests
import sys

# Configuration
URL = 'https://metro.equdaierp.com'
DB = 'metrodb'
USER = 'admin'
PASSWORD = 'Amaze@321'

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
            response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers)
            return response.json()
        except Exception as e:
            print(f"RPC Error: {e}")
            return {}

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
        if result.get('error'):
            print(f"RPC Error ({method}): {result['error']}")
            return None
        return result.get('result')

def main():
    print("Connecting...")
    client = OdooJsonRpcClient(URL, DB, USER, PASSWORD)
    if not client.authenticate():
        print("Authentication Failed")
        return

    print("Authenticated.")

    # 1. Check Full Name of Tag 10T, 10B
    print("\nChecking Tag 10 Names...")
    tags = client.execute_kw('account.account.tag', 'read', [[28, 29]], {'fields': ['name']})
    for t in tags:
        print(f"ID {t['id']}: {t['name']}")

    # 2. Find Company 'mysore restaurant'
    companies = client.execute_kw('res.company', 'search_read', 
        [[('name', 'ilike', 'mysore')]], 
        {'fields': ['id', 'name']})
    
    if not companies:
        print("Company 'mysore' not found.")
        return
    company_id = companies[0]['id']

    # 3. Check Vendor Bills (Posted, 2025)
    print("\nChecking Vendor Bills...")
    domain = [
        ('move_type', '=', 'in_invoice'),
        ('company_id', '=', company_id),
        ('state', '=', 'posted'),
        ('invoice_date', '>=', '2025-01-01')
    ]
    
    invoices = client.execute_kw('account.move', 'search_read', [domain], 
        {'fields': ['name', 'amount_total', 'amount_tax', 'invoice_line_ids'], 'limit': 5})

    if not invoices:
        print("No posted vendor bills found for 2025.")
        return

    print(f"Found {len(invoices)} sample bills.")

    for inv in invoices:
        print(f"\nBill: {inv['name']} | Total: {inv['amount_total']} | Tax: {inv['amount_tax']}")
        
        lines = client.execute_kw('account.move.line', 'read', [inv['invoice_line_ids']], 
            {'fields': ['name', 'price_unit', 'tax_ids', 'tax_tag_ids', 'tax_line_id']})
        
        for line in lines:
            # Check for Tax Line
            if line['tax_line_id']:
                print(f"  -> TAX LINE: {line['name']} | Amount: {line['price_unit']}")
                tags = line['tax_tag_ids']
                if tags:
                     tag_names = client.execute_kw('account.account.tag', 'read', [tags], {'fields': ['name']})
                     tn = [t['name'] for t in tag_names]
                     print(f"     Tags: {tn} (IDs: {tags})")
                else:
                     print("     Tags: NONE")
            
            # Check for Product Line
            elif line['tax_ids']:
                print(f"  -> PROD LINE: {line['name']} | Amount: {line['price_unit']}")
                tags = line['tax_tag_ids']
                if tags:
                     tag_names = client.execute_kw('account.account.tag', 'read', [tags], {'fields': ['name']})
                     tn = [t['name'] for t in tag_names]
                     print(f"     Tags: {tn} (IDs: {tags})")
                else:
                     print("     Tags: NONE")

if __name__ == "__main__":
    main()
