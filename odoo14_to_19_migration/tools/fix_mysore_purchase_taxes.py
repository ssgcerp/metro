import json
import random
import requests
import sys

# Configuration
URL = 'https://metro.equdaierp.com'
DB = 'metrodb'
USER = 'admin'
PASSWORD = 'Amaze@321'

# Constants
TAX_NAME_SEARCH = 'VAT MS'
# Current (Wrong/Generic) Tags
TAG_9T = 26
TAG_9B = 27
# Target (Abu Dhabi) Tags
TAG_10T = 28
TAG_10B = 29

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

    # 1. Find Tax
    taxes = client.execute_kw('account.tax', 'search_read', 
        [[('name', 'ilike', TAX_NAME_SEARCH), ('type_tax_use', '=', 'purchase')]], 
        {'fields': ['id', 'name', 'invoice_repartition_line_ids']})
    
    if not taxes:
        print(f"ERROR: Purchase Tax '{TAX_NAME_SEARCH}' not found!")
        return
    
    tax = taxes[0]
    tax_id = tax['id']
    print(f"Found Purchase Tax: {tax['name']} (ID: {tax_id})")

    # 2. Update Tax Repartition Configuration
    # We need to swap 9T -> 10T and 9B -> 10B
    print("Updating Tax Configuration...")
    
    # Check Base Repartition (Expects 9B -> Needs 10B)
    base_rep_lines = client.execute_kw('account.tax.repartition.line', 'search_read', 
        [[('id', 'in', tax['invoice_repartition_line_ids']), ('repartition_type', '=', 'base')]], 
        {'fields': ['id', 'tag_ids']})
    
    if base_rep_lines:
        brep = base_rep_lines[0]
        current_tags = brep.get('tag_ids', [])
        
        # Determine ops
        ops = []
        if TAG_9B in current_tags:
            ops.append((3, TAG_9B))
        if TAG_10B not in current_tags:
            ops.append((4, TAG_10B))
            
        if ops:
            print(f"  -> Updating Base Repartition {brep['id']} (Remove 9B, Add 10B)...")
            client.execute_kw('account.tax.repartition.line', 'write', [[brep['id']], {'tag_ids': ops}])
        else:
            print("  -> Base Repartition already correct.")
    
    # Check Tax Repartition (Expects 9T -> Needs 10T)
    tax_rep_lines = client.execute_kw('account.tax.repartition.line', 'search_read', 
        [[('id', 'in', tax['invoice_repartition_line_ids']), ('repartition_type', '=', 'tax')]], 
        {'fields': ['id', 'tag_ids']})
        
    if tax_rep_lines:
        trep = tax_rep_lines[0]
        current_tags = trep.get('tag_ids', [])
        
        ops = []
        if TAG_9T in current_tags:
            ops.append((3, TAG_9T))
        if TAG_10T not in current_tags:
            ops.append((4, TAG_10T))

        if ops:
             print(f"  -> Updating Tax Repartition {trep['id']} (Remove 9T, Add 10T)...")
             client.execute_kw('account.tax.repartition.line', 'write', [[trep['id']], {'tag_ids': ops}])
        else:
            print("  -> Tax Repartition already correct.")


    # 3. UPDATE EXISTING VENDOR BILL LINES (2025)
    print("\nUpdating Existing Vendor Bill Lines...")
    
    domain = [
        ('tax_ids', 'in', [tax_id]), # Filter by lines using this tax (implicitly product lines, or tax lines linked to it) or just all lines
        # Actually safer to check all lines of bills where this tax is used.
        # But looking at previous scripts, we can just search lines.
        # However, tax lines don't have 'tax_ids', they have 'tax_line_id'.
    ]
    
    # A. Product Lines (Base) -> Switch 9B to 10B
    print("  -> Checking Product Lines...")
    domain_prod = [
        ('tax_ids', 'in', [tax_id]),
        ('parent_state', '=', 'posted'),
        ('date', '>=', '2025-01-01')
    ]
    prod_lines = client.execute_kw('account.move.line', 'search_read', [domain_prod], {'fields': ['id', 'tax_tag_ids']})
    
    batch_prod = []
    for line in prod_lines:
        tags = line.get('tax_tag_ids', [])
        if TAG_9B in tags and TAG_10B not in tags:
            batch_prod.append(line['id'])
    
    if batch_prod:
        print(f"     Updating {len(batch_prod)} product lines...")
        # (3, 9B), (4, 10B)
        client.execute_kw('account.move.line', 'write', [batch_prod, {'tax_tag_ids': [(3, TAG_9B), (4, TAG_10B)]}],
                          {'context': {'check_move_validity': False}})
    else:
        print("     Product lines up to date.")

    # B. Tax Lines (Tax) -> Switch 9T to 10T
    print("  -> Checking Tax Lines...")
    domain_tax = [
        ('tax_line_id', '=', tax_id),
        ('parent_state', '=', 'posted'),
        ('date', '>=', '2025-01-01')
    ]
    tax_lines = client.execute_kw('account.move.line', 'search_read', [domain_tax], {'fields': ['id', 'tax_tag_ids']})
    
    batch_tax = []
    for line in tax_lines:
        tags = line.get('tax_tag_ids', [])
        if TAG_9T in tags and TAG_10T not in tags:
            batch_tax.append(line['id'])

    if batch_tax:
        print(f"     Updating {len(batch_tax)} tax lines...")
        # (3, 9T), (4, 10T)
        client.execute_kw('account.move.line', 'write', [batch_tax, {'tax_tag_ids': [(3, TAG_9T), (4, TAG_10T)]}],
                          {'context': {'check_move_validity': False}})
    else:
        print("     Tax lines up to date.")

    print("\nDone.")

if __name__ == "__main__":
    main()
