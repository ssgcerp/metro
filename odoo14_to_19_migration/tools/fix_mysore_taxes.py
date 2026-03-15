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
TAG_NAME_SEARCH = '1(a)T'   # Abu Dhabi Standard Rated Supplies

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

    # 1. Find the Tag ID
    print(f"Searching for Tag '{TAG_NAME_SEARCH}'...")
    tags = client.execute_kw('account.account.tag', 'search_read', 
        [[('name', '=', TAG_NAME_SEARCH)]], 
        {'fields': ['id', 'name']})
    
    if not tags:
        print(f"ERROR: Tag '{TAG_NAME_SEARCH}' not found!")
        return
    
    target_tag_id = tags[0]['id']
    print(f"Target Tag: {tags[0]['name']} (ID: {target_tag_id})")

    # 2. Find the Tax
    print(f"Searching for Tax '{TAX_NAME_SEARCH}'...")
    taxes = client.execute_kw('account.tax', 'search_read', 
        [[('name', 'ilike', TAX_NAME_SEARCH), ('type_tax_use', '=', 'sale')]], 
        {'fields': ['id', 'name', 'invoice_repartition_line_ids']})
    
    if not taxes:
        print(f"ERROR: Tax '{TAX_NAME_SEARCH}' not found!")
        return
    
    tax = taxes[0]
    tax_id = tax['id']
    print(f"Found Tax: {tax['name']} (ID: {tax_id})")

    # 3. Fix Tax Configuration (Repartition Line)
    print("Checking Tax Configuration...")
    rep_lines = client.execute_kw('account.tax.repartition.line', 'search_read', 
        [[('id', 'in', tax['invoice_repartition_line_ids']), ('repartition_type', '=', 'tax')]], 
        {'fields': ['id', 'tag_ids']})
    
    if not rep_lines:
        print("ERROR: No 'tax' repartition line found for this tax.")
        return

    rep_line = rep_lines[0]
    rep_line_id = rep_line['id']
    current_tags = rep_line.get('tag_ids', [])
    
    if target_tag_id in current_tags:
        print("  -> Tax configuration already correct.")
    else:
        print(f"  -> Adding tag {target_tag_id} to repartition line {rep_line_id}...")
        # Write to repartition line
        # Using (4, ID) to add relation
        update_result = client.execute_kw('account.tax.repartition.line', 'write', 
             [[rep_line_id], {'tag_ids': [(4, target_tag_id)]}])
        
        if update_result:
             print("  -> Tax Configuration UPDATED.")
        else:
             print("  -> FAILED to update Tax Configuration.")

    # 4. Update Existing Invoice Lines
    print("\nScanning for existing invoice lines to update (2025+)...")
    
    # We find lines that use this tax, are posted, and are recent
    domain_lines = [
        ('tax_ids', 'in', [tax_id]),
        ('parent_state', '=', 'posted'),
        ('date', '>=', '2025-01-01')
    ]
    
    # We fetch ALL potential lines, then filter locally for tag check
    # Fetching 'tax_tag_ids' to check if update is needed
    lines_to_fix = []
    
    offset = 0
    limit = 100
    while True:
        lines = client.execute_kw('account.move.line', 'search_read', [domain_lines], 
            {'fields': ['id', 'name', 'tax_tag_ids', 'move_id'], 'limit': limit, 'offset': offset})
        
        if not lines:
            break
            
        for line in lines:
            if target_tag_id not in line.get('tax_tag_ids', []):
                lines_to_fix.append(line['id'])
        
        offset += limit
        print(f"Scanned {offset} lines... Found {len(lines_to_fix)} to fix so far.", end='\r')

    print(f"\nFound {len(lines_to_fix)} invoice lines missing the tag.")

    if not lines_to_fix:
        print("No lines to update.")
        return

    # Update Lines
    print(f"Updating {len(lines_to_fix)} lines... (Adding tag {target_tag_id})")
    
    batch_size = 50
    success_count = 0
    
    # We attempt to write using context to skip constraint checks if possible
    # We write directly to 'tax_tag_ids'
    
    try:
        total_batches = (len(lines_to_fix) // batch_size) + 1
        for i in range(0, len(lines_to_fix), batch_size):
            batch = lines_to_fix[i:i+batch_size]
            
            # Context to bypass certain checks (if server respects it for write)
            ctx = {'check_move_validity': False} # Common Odoo context to skip balance checks
            
            # Using call_kw with context in kwargs
            # (4, ID) adds the tag
            res = client.execute_kw('account.move.line', 'write', [batch, {'tax_tag_ids': [(4, target_tag_id)]}], {'context': ctx})
            
            if res:
                success_count += len(batch)
                print(f"Batch {i//batch_size + 1}/{total_batches} done. Total updated: {success_count}", end='\r')
            else:
                print(f"Batch {i//batch_size + 1} failed (returned False).")

    except Exception as e:
        print(f"\nUpdate failed with error: {e}")
        
    print(f"\nFinished. Successfully updated {success_count} lines.")

if __name__ == "__main__":
    main()
