import json
import random
import sys
import time
import requests
import argparse
import logging

# Configure logging
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
                pass
            return res_json
        except Exception as e:
            print(f"RPC EXCEPTION: {e}")
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
        if result and 'error' in result:
             return None
        return result.get('result')

def main():
    parser = argparse.ArgumentParser(description='Check Missing Dependencies for Customer Payments')
    # Odoo 14 Defaults
    parser.add_argument('--src-url', default='https://erpmfs.com', help='Source Odoo 14 URL')
    parser.add_argument('--src-db', default='metro_production_8_8_22', help='Source Odoo 14 DB')
    parser.add_argument('--src-user', default='Sales.auh@metrofiresystems.com', help='Source Odoo 14 User')
    parser.add_argument('--src-password', default='Sales@185734', help='Source Odoo 14 Password')

    # Odoo 19 Defaults
    parser.add_argument('--dest-url', default='http://localhost:8079', help='Dest Odoo 19 URL')
    parser.add_argument('--dest-db', default='metrodb', help='Dest Odoo 19 DB')
    parser.add_argument('--dest-user', default='admin', help='Dest Odoo 19 User')
    parser.add_argument('--dest-password', default='Amaze@321', help='Dest Odoo 19 Password')
    
    parser.add_argument('--limit', type=int, default=0, help='Limit number of records (0 for all)')

    args = parser.parse_args()

    print("\n" + "="*80)
    print(f"CHECKING MISSING DEPENDENCIES (Journals & Partners)")
    print("="*80)

    # 1. Connect
    src_client = OdooJsonRpcClient(args.src_url, args.src_db, args.src_user, args.src_password)
    valid_src = src_client.authenticate()

    dest_client = OdooJsonRpcClient(args.dest_url, args.dest_db, args.dest_user, args.dest_password)
    valid_dest = dest_client.authenticate()

    if not valid_src:
        print("CRITICAL: Failed to authenticate with Source Odoo 14.")
        sys.exit(1)
    if not valid_dest:
        print("CRITICAL: Failed to authenticate with Destination Odoo 19.")
        print(f"URL: {args.dest_url}, DB: {args.dest_db}")
        sys.exit(1)

    print("Connected to Source and Destination.")

    # 2. Fetch Source Data
    print("Fetching Source Data (Customer Payments)...")
    
    try:
        domain = [
            ('payment_type', '=', 'inbound'),
            ('partner_type', '=', 'customer'),
            ('state', '=', 'posted')
        ]
        fields_v14 = ['journal_id', 'partner_id']
        payments_v14 = src_client.execute_kw('account.payment', 'search_read', [domain, fields_v14])
        
        if args.limit > 0 and payments_v14:
            payments_v14 = payments_v14[:args.limit]
            
        print(f"Scanning {len(payments_v14) if payments_v14 else 0} payments...")
        
        used_journals = set()
        used_partners = set()
        
        if payments_v14:
            for p in payments_v14:
                if p['journal_id']:
                    used_journals.add(p['journal_id'][1])
                if p['partner_id']:
                    used_partners.add(p['partner_id'][1])
                        
    except Exception as e:
        print(f"Error scanning source: {e}")
        sys.exit(1)

    print(f"\nFound {len(used_journals)} unique Journals used.")
    print(f"Found {len(used_partners)} unique Partners used.")

    # 3. Check Destination
    print("\nChecking existence in Destination (Odoo 19)...")
    
    missing_journals = []
    found_journals = 0
    
    # Check Journals
    for j_name in used_journals:
        # Check if journal exists in any company for now, or assume main company context
        # Better to check by name globally
        res = dest_client.execute_kw('account.journal', 'search_count', [[('name', '=', j_name)]])
        if res and res > 0:
            found_journals += 1
        else:
            # Try searching by type='bank' and name similar? No, strict check first.
            missing_journals.append(j_name)
    
    # Check Partners (Sample check or full check)
    # Checking thousands of partners might be slow, so we'll just report count of missing
    missing_partners_count = 0
    missing_partners_sample = []
    
    # Batch check partners for speed? 
    # Or just loop. Loop is slow for thousands. 
    # Let's check a sample or all if < 500
    check_partners = list(used_partners)
    if len(check_partners) > 1000:
        print("Checking first 1000 partners only...")
        check_partners = check_partners[:1000]

    for p_name in check_partners:
        res = dest_client.execute_kw('res.partner', 'search_count', [[('name', '=', p_name)]])
        if not res or res == 0:
            missing_partners_count += 1
            if len(missing_partners_sample) < 10:
                missing_partners_sample.append(p_name)

    # 4. Report
    print("\n" + "="*80)
    print("MISSING DEPENDENCIES REPORT")
    print("="*80)
    
    print("\n[MISSING JOURNALS]")
    if missing_journals:
        for m in sorted(missing_journals):
            print(f" - {m}")
    else:
        print(" NONE (All present)")
        
    print("\n[MISSING PARTNERS (Sample)]")
    if missing_partners_count > 0:
        print(f" Total Missing (in checked batch): {missing_partners_count}")
        print(" Sample missing partners:")
        for m in missing_partners_sample:
            print(f" - {m}")
    else:
        print(" NONE ( All checked partners present)")
        
    print("\n" + "="*80)
    print(f"Summary: Missing {len(missing_journals)} Journals.")

if __name__ == '__main__':
    main()
