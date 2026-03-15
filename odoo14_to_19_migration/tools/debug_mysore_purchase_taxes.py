import json
import random
import requests

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

    # 1. Find Company 'mysore restaurant'
    companies = client.execute_kw('res.company', 'search_read', 
        [[('name', 'ilike', 'mysore')]], 
        {'fields': ['id', 'name']})
    
    if not companies:
        print("Company 'mysore' not found.")
        return
    company_id = companies[0]['id']
    print(f"Company: {companies[0]['name']} (ID: {company_id})")

    # 2. Find Purchase Taxes
    print("\nSearching for Purchase Taxes...")
    # Typically 'VAT MS (Purchase)' or similar. Or maybe just standard VAT 5% used.
    # Let's list all purchase taxes for this company.
    taxes = client.execute_kw('account.tax', 'search_read', 
        [[('company_id', '=', company_id), ('type_tax_use', '=', 'purchase')]], 
        {'fields': ['id', 'name', 'amount', 'invoice_repartition_line_ids']})
    
    if not taxes:
        print("No Purchase taxes found!")
    
    for tax in taxes:
        print(f"Tax: {tax['name']} ({tax['amount']}%)")
        
        # Check Configuration
        rep_lines = client.execute_kw('account.tax.repartition.line', 'read', 
            [tax['invoice_repartition_line_ids']], 
            {'fields': ['repartition_type', 'tag_ids']})
        
        has_tags = False
        for rep in rep_lines:
            if rep['tag_ids']:
                has_tags = True
                tags = client.execute_kw('account.account.tag', 'read', [rep['tag_ids']], {'fields': ['name', 'id']})
                t_info = [f"{t['name']} (ID: {t['id']})" for t in tags]
                print(f"  -> Repartition ({rep['repartition_type']}): {t_info}")
        
        if not has_tags:
            print("  -> WARNING: No tags configured!")

    # 3. Search for Abu Dhabi Purchase Tags
    print("\nSearching for Abu Dhabi Purchase Tags (10...):")
    # Usually grid 10.
    tags = client.execute_kw('account.account.tag', 'search_read', 
        [[('name', 'like', '10%')]], 
        {'fields': ['id', 'name']})
        
    # 4. Compare with a 'Good' Tax from Company 1 (likely 'Metro')
    print("\n--- Comparing with Standard Purchase Tax (Company 1) ---")
    good_taxes = client.execute_kw('account.tax', 'search_read', 
        [[('company_id', '=', 1), ('type_tax_use', '=', 'purchase'), ('amount', '=', 5.0)]], 
        {'fields': ['name', 'invoice_repartition_line_ids'], 'limit': 1})
    
    if good_taxes:
        gtax = good_taxes[0]
        print(f"Reference Tax: {gtax['name']}")
        rep_lines = client.execute_kw('account.tax.repartition.line', 'read', 
            [gtax['invoice_repartition_line_ids']], 
            {'fields': ['repartition_type', 'tag_ids']})
        
        for rep in rep_lines:
             tag_ids = rep.get('tag_ids', [])
             if tag_ids:
                 tags = client.execute_kw('account.account.tag', 'read', [tag_ids], {'fields': ['name']})
                 tag_names = [t['name'] for t in tags]
                 print(f"  -> Repartition ({rep['repartition_type']}): {tag_names} (IDs: {tag_ids})")

if __name__ == "__main__":
    main()
