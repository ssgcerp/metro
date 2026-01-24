
import json
import random
import sys
import requests
import argparse
import logging
import pandas as pd
import shutil
import os

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
    parser = argparse.ArgumentParser(description='Fix Petty Cash Journals in Excel')
    parser.add_argument('--url', required=True, help='Odoo URL')
    parser.add_argument('--db', required=True, help='Odoo DB')
    parser.add_argument('--user', required=True, help='Odoo User')
    parser.add_argument('--password', required=True, help='Odoo Password')
    parser.add_argument('--file', required=True, help='Excel Import File')
    
    args = parser.parse_args()

    print("\n" + "="*80)
    print("FIXING PETTY CASH JOURNALS")
    print("="*80)

    # 1. Connect to Odoo
    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    if not client.authenticate():
        print("Authentication failed to Odoo 19!")
        sys.exit(1)
    print("Connected to Odoo 19.")

    # 2. Read Excel
    if not os.path.exists(args.file):
        print(f"File not found: {args.file}")
        sys.exit(1)
        
    # Backup
    backup_path = args.file + "_BACKUP_ADVANCED.xlsx"
    shutil.copy2(args.file, backup_path)
    print(f"Backed up to: {backup_path}")

    df = pd.read_excel(args.file)
    print(f"Loaded {len(df)} rows.")

    updated_count = 0
    
    # Cache for companies
    # company_name -> journal_name (mapping)
    company_map = {
        'RAS AL KHAIMAH': 'Petty Cash - RAK',
        'SHARJAH': 'Petty Cash - SHJ',
        'FUJAIRAH': 'Petty Cash - Fujairah',
        'DUBAI': 'Petty Cash - DUBAI',
        'ABU DHABI': 'Petty Cash - Abu Dhabi', 
        # Add broad fuzzy matching if needed in logic
    }

    for index, row in df.iterrows():
        current_journal = str(row.get('Journal', '')).strip()
        
        if current_journal == "Office Petty Cash":
            new_journal = None
            
            # METHOD 1: LINKED BILL -> COMPANY
            bill_nums_raw = str(row.get('Linked Bill Numbers', ''))
            bill_names = [b.strip() for b in bill_nums_raw.split(',') if b.strip() and b.lower() != 'nan']
            
            if bill_names:
                # Optimized: We could batch search, but for simplicity/safety loop is okay or search single first
                # Find the first valid bill
                found_bill = client.execute_kw('account.move', 'search_read', 
                                              [[('move_type', '=', 'in_invoice'), ('name', 'in', bill_names)]], 
                                              {'fields': ['company_id'], 'limit': 1})
                if found_bill and found_bill[0]['company_id']:
                    c_name = found_bill[0]['company_id'][1].upper() # 0=id, 1=name
                    
                    # Fuzzy / Direct Map
                    if 'RAS AL KHAIMAH' in c_name: new_journal = 'Petty Cash - RAK'
                    elif 'SHARJAH' in c_name: new_journal = 'Petty Cash - SHJ'
                    elif 'FUJAIRAH' in c_name: new_journal = 'Petty Cash - Fujairah'
                    elif 'DUBAI' in c_name: new_journal = 'Petty Cash - DUBAI'
                    elif 'ABU DHABI' in c_name: new_journal = 'Petty Cash - Abu Dhabi'
                    
                    if new_journal:
                        print(f"Row {index+2}: Mapped via Bill Company '{c_name}' -> {new_journal}")

            # METHOD 2: MEMO FALLBACK
            if not new_journal:
                memo = str(row.get('Memo/Ref', '')).upper()
                if 'RAK' in memo or 'RAS AL KHAIMAH' in memo:
                    new_journal = "Petty Cash - RAK"
                elif 'FAIZ' in memo or 'ARSHAD' in memo or 'SHARJAH' in memo:
                     new_journal = "Petty Cash - SHJ"
                elif 'FUJ' in memo:
                     new_journal = "Petty Cash - Fujairah"
                elif 'ALAM' in memo or 'MUBARAK' in memo or 'DUBAI' in memo:
                     new_journal = "Petty Cash - DUBAI"
                
                if new_journal:
                    print(f"Row {index+2}: Mapped via Memo '{memo[:20]}...' -> {new_journal}")
            
            # UPDATE
            if new_journal:
                df.at[index, 'Journal'] = new_journal
                updated_count += 1
                
    # 3. Save
    if updated_count > 0:
        df.to_excel(args.file, index=False)
        print(f"\nSaved updated file to: {args.file}")
        print(f"Total rows updated: {updated_count}")
    else:
        print("\nNo entries matched criteria. File matched unchanged.")

if __name__ == "__main__":
    main()
