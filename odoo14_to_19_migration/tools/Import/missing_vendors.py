
import json
import random
import sys
import requests
import argparse
import logging
import pandas as pd

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
                print(f"\nRPC ERROR: {res_json['error']}\n")
                return res_json
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
        if hasattr(result, 'get_result'):
             return result.get_result()
        return result.get('result')

def main():
    parser = argparse.ArgumentParser(description='Report Missing Vendors from Excel')
    parser.add_argument('--url', required=True, help='Odoo URL')
    parser.add_argument('--db', required=True, help='Odoo DB')
    parser.add_argument('--user', required=True, help='Odoo User')
    parser.add_argument('--password', required=True, help='Odoo Password')
    parser.add_argument('--file', required=True, help='Excel Import File')
    
    args = parser.parse_args()

    print("\n" + "="*80)
    print(f"CHECKING MISSING VENDORS: {args.file}")
    print("="*80)

    # 1. Read Excel
    try:
        df = pd.read_excel(args.file)
    except FileNotFoundError:
        print(f"File not found: {args.file}")
        sys.exit(1)

    df.columns = df.columns.str.strip()
    
    if 'Partner' not in df.columns:
        print("Error: 'Partner' column not found in Excel.")
        sys.exit(1)
        
    excel_vendors = set(df['Partner'].dropna().astype(str).str.strip().unique())
    print(f"Found {len(excel_vendors)} unique vendors in Excel.")

    # 2. Connect to Odoo
    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    if not client.authenticate():
        print("Authentication failed to Odoo 19!")
        sys.exit(1)
    print("Connected to Odoo 19.")

    # 3. Check Vendors
    # Since there might be many, checking one by one or in batches is safer than fetching all partners if db is huge.
    # But fetching all names is usually okay if < 100k partners.
    # Let's fetch all partner names first for speed.
    
    print("Fetching Odoo Partners...")
    # Only fetch suppliers? Or all partners? Safe to fetch all names.
    odoo_partners = client.execute_kw('res.partner', 'search_read', [[], ['name']])
    odoo_partner_names = set()
    if odoo_partners:
        for p in odoo_partners:
            odoo_partner_names.add(p['name'].strip())
            # Also handle lowercase for loose matching?
            # odoo_partner_names.add(p['name'].strip().lower())
            
    print(f"Found {len(odoo_partner_names)} partners in Odoo.")
    
    missing = []
    
    # We can try case-insensitive match too
    odoo_partners_lower = {n.lower() for n in odoo_partner_names}
    
    for ev in excel_vendors:
        if ev in odoo_partner_names:
            continue
        elif ev.lower() in odoo_partners_lower:
             continue
        else:
            missing.append(ev)
            
    # 4. Report
    print("\n" + "="*80)
    print("MISSING VENDORS REPORT (In Excel but NOT in Odoo 19)")
    print("="*80)
    
    if missing:
        for m in sorted(missing):
            print(f"[MISSING] {m}")
    else:
        print("Good news! All vendors from Excel exist in Odoo 19.")

    print("\nDone.")

if __name__ == "__main__":
    main()
