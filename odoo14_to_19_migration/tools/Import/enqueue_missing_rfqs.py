import argparse
import requests
import json
import random
import sys

# -----------------------------------------------------------------------------
# Odoo JSON-RPC Client
# -----------------------------------------------------------------------------
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
            response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers, timeout=60)
            return response.json()
        except Exception as e:
            print(f"RPC Error to {self.url}: {e}")
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

def fetch_po_names(client, system_name, domain=None):
    if domain is None: domain = []
    print(f"Fetching POs/RFQs from {system_name}...")
    
    count = client.execute_kw('purchase.order', 'search_count', [domain])
    print(f"  Found {count} records in {system_name}.")
    
    if not count:
        return set()
        
    # Batch fetch
    batch_size = 1000
    all_names = set()
    
    ids = client.execute_kw('purchase.order', 'search', [domain])
    if not ids: return set()
    
    total = len(ids)
    for i in range(0, total, batch_size):
        batch = ids[i:i+batch_size]
        res = client.execute_kw('purchase.order', 'read', [batch, ['name']])
        if res:
            for r in res:
                if r.get('name'):
                    all_names.add(r['name'])
        print(f"  Fetched {len(all_names)}/{total}...", end='\r')
    print()
    return all_names

def fetch_queued_rfq_names(client):
    print("Fetching already queued RFQs from Odoo 19...")
    domain = [] # Fetch all
    count = client.execute_kw('rfq.migration.line', 'search_count', [domain])
    print(f"  Found {count} records in queue.")
    
    if not count:
        return set()
    
    # Batch fetch
    batch_size = 1000
    all_names = set()
    
    ids = client.execute_kw('rfq.migration.line', 'search', [domain])
    if not ids: return set()
    
    total = len(ids)
    for i in range(0, total, batch_size):
        batch = ids[i:i+batch_size]
        res = client.execute_kw('rfq.migration.line', 'read', [batch, ['uploaded_rfq_number']])
        if res:
            for r in res:
                if r.get('uploaded_rfq_number'):
                    all_names.add(r['uploaded_rfq_number'])
        print(f"  Fetched {len(all_names)}/{total}...", end='\r')
    print()
    return all_names

def main():
    parser = argparse.ArgumentParser(description='Enqueue Missing RFQs')
    
    # Defaults
    parser.add_argument('--o14-url', default='https://erpmfs.com')
    parser.add_argument('--o14-db', default='metro_production_8_8_22')
    parser.add_argument('--o14-user', default='Sales.auh@metrofiresystems.com')
    parser.add_argument('--o14-pass', default='Sales@185734')
    
    parser.add_argument('--o19-url', default='https://metro.equdaierp.com')
    parser.add_argument('--o19-db', default='metrodb')
    parser.add_argument('--o19-user', default='admin')
    parser.add_argument('--o19-pass', default='Amaze@321')
    
    parser.add_argument('--execute', action='store_true', help='Actually enqueue the missing RFQs. If not set, checks only.')
    
    args = parser.parse_args()

    # 1. Authenticate Odoo 19 (Destination)
    print("Connecting to Odoo 19...")
    client19 = OdooJsonRpcClient(args.o19_url, args.o19_db, args.o19_user, args.o19_pass)
    if not client19.authenticate():
        print("Failed to auth with Odoo 19")
        return

    # 2. Authenticate Odoo 14 (Source)
    print("Connecting to Odoo 14...")
    client14 = OdooJsonRpcClient(args.o14_url, args.o14_db, args.o14_user, args.o14_pass)
    if not client14.authenticate():
        print("Failed to auth with Odoo 14")
        return

    # 3. Fetch RFQs from Odoo 14
    # RFQ States: draft, sent, to approve
    rfq_domain = [('state', 'in', ['draft', 'sent', 'to approve'])]
    rfq_names14 = fetch_po_names(client14, "Odoo 14 (RFQs)", rfq_domain)
    
    # 4. Fetch ALL POs from Odoo 19 (to check if they exist AT ALL)
    all_names19 = fetch_po_names(client19, "Odoo 19 (All POs)")
    
    # 5. Fetch already queued RFQs in Odoo 19
    queued_names19 = fetch_queued_rfq_names(client19)
    
    # 6. Identify Missing
    # Missing = Odoo 14 RFQs - (Odoo 19 POs + Odoo 19 Queue)
    missing = rfq_names14 - all_names19 - queued_names19
    
    print(f"\nAnalysis Results:")
    print(f"  Odoo 14 RFQs: {len(rfq_names14)}")
    print(f"  Odoo 19 Total POs: {len(all_names19)}")
    print(f"  Odoo 19 Queued RFQs: {len(queued_names19)}")
    print(f"  Missing & Not Queued: {len(missing)}")
    
    if not missing:
        print("No missing RFQs to enqueue.")
        return
        
    if not args.execute:
        print("\nRun with --execute to enqueue these RFQs.")
        return

    # 7. Get Migration Config ID
    print("\nFetching Migration Configuration...")
    configs = client19.execute_kw('odoo14.migration.config', 'search_read', [[], ['id', 'name']], {'limit': 1})
    if not configs:
        print("❌ No migration configuration found in Odoo 19! Please create one first.")
        return
    config_id = configs[0]['id']
    print(f"Using Migration Config: {configs[0]['name']} (ID: {config_id})")
    
    # 8. Enqueue Missing RFQs
    print(f"\nEnqueueing {len(missing)} missing RFQs...")
    
    batch_size = 50
    missing_list = sorted(list(missing))
    total_created = 0
    
    for i in range(0, len(missing_list), batch_size):
        batch = missing_list[i:i+batch_size]
        
        # Determine status/excel_status
        # Use 'pending_migration' as default status
        
        # Prepare create values
        create_vals = []
        for rfq_name in batch:
            create_vals.append({
                'uploaded_rfq_number': rfq_name,
                'status': 'pending_migration',
                'excel_status': 'Missing in Odoo 19 (Auto-Enqueued)',
                'stage': 'Draft', # Default assumption
                'config_id': config_id,
                'priority': 'Normal',
                'company': 'Unknown', # Will be fetched during migration
            })
            
        try:
            # Batch create
            client19.execute_kw('rfq.migration.line', 'create', [create_vals])
            total_created += len(batch)
            print(f"  Enqueued {total_created}/{len(missing)}...", end='\r')
        except Exception as e:
            print(f"\nError enqueuing batch: {e}")
            
    print(f"\n✅ Successfully enqueued {total_created} RFQs.")

if __name__ == '__main__':
    main()
