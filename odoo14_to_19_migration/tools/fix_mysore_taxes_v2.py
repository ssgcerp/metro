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
TAG_TAX_NAME = '1(a)T'
TAG_BASE_NAME = '1(a)B'

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

    # 1. Resolve Tags
    print("Resolving Tags...")
    tags = client.execute_kw('account.account.tag', 'search_read', 
        [[('name', 'in', [TAG_TAX_NAME, TAG_BASE_NAME])]], 
        {'fields': ['id', 'name']})
    
    tag_tax_id = None
    tag_base_id = None
    
    for t in tags:
        if t['name'] == TAG_TAX_NAME:
            tag_tax_id = t['id']
        elif t['name'] == TAG_BASE_NAME:
            tag_base_id = t['id']
            
    if not tag_tax_id or not tag_base_id:
        print(f"ERROR: Could not find one or both tags. Tax: {tag_tax_id}, Base: {tag_base_id}")
        return

    print(f"Tag Base (for Products): {tag_base_id} ({TAG_BASE_NAME})")
    print(f"Tag Tax (for Tax Lines): {tag_tax_id} ({TAG_TAX_NAME})")

    # 2. Find Tax
    taxes = client.execute_kw('account.tax', 'search_read', 
        [[('name', 'ilike', TAX_NAME_SEARCH), ('type_tax_use', '=', 'sale')]], 
        {'fields': ['id', 'name', 'invoice_repartition_line_ids']})
    
    if not taxes:
        print(f"ERROR: Tax '{TAX_NAME_SEARCH}' not found!")
        return
    
    tax = taxes[0]
    tax_id = tax['id']
    print(f"Found Tax: {tax['name']} (ID: {tax_id})")

    # 3. Update Tax Repartition Configuration (Standard practice: Base Tag on Base Repartition, Tax Tag on Tax Repartition)
    # Check Base Repartition
    print("Checking Tax Configuration...")
    base_rep_lines = client.execute_kw('account.tax.repartition.line', 'search_read', 
        [[('id', 'in', tax['invoice_repartition_line_ids']), ('repartition_type', '=', 'base')]], 
        {'fields': ['id', 'tag_ids']})
    
    if base_rep_lines:
        brep = base_rep_lines[0]
        if tag_base_id not in brep.get('tag_ids', []):
            print(f"  -> Adding Base Tag to Repartition Line {brep['id']}...")
            client.execute_kw('account.tax.repartition.line', 'write', [[brep['id']], {'tag_ids': [(4, tag_base_id)]}])
    else:
        print("  -> WARNING: No Base Repartition Line found!")

    # Check Tax Repartition (We did this before, just verifying)
    tax_rep_lines = client.execute_kw('account.tax.repartition.line', 'search_read', 
        [[('id', 'in', tax['invoice_repartition_line_ids']), ('repartition_type', '=', 'tax')]], 
        {'fields': ['id', 'tag_ids']})
        
    if tax_rep_lines:
        trep = tax_rep_lines[0]
        if tag_tax_id not in trep.get('tag_ids', []):
             print(f"  -> Adding Tax Tag to Repartition Line {trep['id']}...")
             client.execute_kw('account.tax.repartition.line', 'write', [[trep['id']], {'tag_ids': [(4, tag_tax_id)]}])

    # 4. FIX PRODUCT LINES (Base Amount)
    # These are lines that have the Tax applied in 'tax_ids'
    # Action: Remove Tax Tag (ID 4), Add Base Tag (ID 5)
    
    print("\ncorrecting PRODUCT LINES (Base Amount)...")
    domain_prod = [
        ('tax_ids', 'in', [tax_id]),
        ('parent_state', '=', 'posted'),
        ('date', '>=', '2025-01-01')
    ]
    
    prod_lines = client.execute_kw('account.move.line', 'search_read', [domain_prod], {'fields': ['id', 'tax_tag_ids']}) # Fetch all at once if small enough
    print(f"Found {len(prod_lines)} product lines to check.")
    
    batch_fix_prod = []
    
    for line in prod_lines:
        current = line.get('tax_tag_ids', [])
        needs_update = False
        ops = []
        
        # Remove Tax Tag if present
        if tag_tax_id in current:
            ops.append((3, tag_tax_id)) # 3 = Remove
            needs_update = True
            
        # Add Base Tag if missing
        if tag_base_id not in current:
            ops.append((4, tag_base_id)) # 4 = Add
            needs_update = True
            
        if needs_update:
            # We can't batch heterogeneous updates easily in one call unless we just force set (6, 0, ids)
            # But calculating final state is safer.
            # actually, if we want to batch, we must find groups with same operations.
            # Simpler: just batch write the same operation if it applies to all.
            # Here, operations might differ per line. 
            # To be safe and since it's < 200 lines, iterating write is okayish, or we group.
            
            # Let's just force the correct state: Remove Tax Tag, Add Base Tag
            # We can do this in batch for ALL lines: Write -> Remove 4, Add 5.
            # Even if 4 isn't there, Remove 4 is safe. Even if 5 is there, Add 5 is safe (deduped).
            batch_fix_prod.append(line['id'])

    if batch_fix_prod:
        print(f"Updating {len(batch_fix_prod)} product lines...")
        # (3, ID) removes relation, (4, ID) adds relation.
        # Order matters? Odoo executes in order.
        client.execute_kw('account.move.line', 'write', [batch_fix_prod, {'tax_tag_ids': [(3, tag_tax_id), (4, tag_base_id)]}],
                          {'context': {'check_move_validity': False}})
        print("Product Lines Updated.")
    else:
        print("Product Lines already correct.")


    # 5. FIX TAX LINES (Tax Amount)
    # These are lines where 'tax_line_id' is the VAT MS tax.
    # Action: Add Tax Tag (ID 4)
    
    print("\nCorrecting TAX LINES (VAT Amount)...")
    domain_tax = [
        ('tax_line_id', '=', tax_id),
        ('parent_state', '=', 'posted'),
        ('date', '>=', '2025-01-01')
    ]
    
    tax_lines = client.execute_kw('account.move.line', 'search_read', [domain_tax], {'fields': ['id', 'tax_tag_ids']})
    print(f"Found {len(tax_lines)} tax lines to check.")
    
    batch_fix_tax = []
    for line in tax_lines:
        if tag_tax_id not in line.get('tax_tag_ids', []):
            batch_fix_tax.append(line['id'])
            
    if batch_fix_tax:
        print(f"Updating {len(batch_fix_tax)} tax lines...")
        client.execute_kw('account.move.line', 'write', [batch_fix_tax, {'tax_tag_ids': [(4, tag_tax_id)]}],
                          {'context': {'check_move_validity': False}})
        print("Tax Lines Updated.")
    else:
        print("Tax Lines already correct.")

    print("\nDone.")

if __name__ == "__main__":
    main()
