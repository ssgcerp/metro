import pandas as pd
import requests
import json
import random
import os
import argparse

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
            response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers, timeout=30)
            return response.json()
        except Exception as e:
            print(f"RPC Connection Failed: {e}")
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

def main():
    parser = argparse.ArgumentParser(description='Analyze Missing Journals and Accounts against Odoo 19')
    export_base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    default_export_dir = os.path.join(export_base_dir, 'Export')
    parser.add_argument('--export-dir', default=default_export_dir, help='Directory containing exported Excel files')
    
    # Odoo 19 Credentials
    parser.add_argument('--dest-url', default='http://localhost:8079', help='Dest Odoo 19 URL')
    parser.add_argument('--dest-db', default='metrodb', help='Dest Odoo 19 User')
    parser.add_argument('--dest-user', default='admin', help='Dest Odoo 19 User')
    parser.add_argument('--dest-password', default='Amaze@321', help='Dest Odoo 19 Password')

    args = parser.parse_args()

    # 1. Read All Excel Files
    print(f"Reading Excel files from {args.export_dir}...")
    
    if not os.path.exists(args.export_dir):
        print(f"Error: Directory {args.export_dir} not found.")
        return

    excel_journals = set()
    excel_accounts = set()

    files = [f for f in os.listdir(args.export_dir) if f.endswith('.xlsx') and not f.startswith('~$')]
    
    if not files:
        print("No Excel files found.")
        return

    for f in files:
        path = os.path.join(args.export_dir, f)
        print(f"  - Reading {f}...")
        try:
            df = pd.read_excel(path)
            
            # Extract Journals
            if 'Journal*' in df.columns:
                journals = df['Journal*'].dropna().unique()
                excel_journals.update(journals)
            
            # Extract Accounts
            if 'Invoice Lines/Account*' in df.columns:
                accounts = df['Invoice Lines/Account*'].dropna().unique()
                excel_accounts.update(accounts)
                
        except Exception as e:
            print(f"    Error reading {f}: {e}")

    print(f"\nFound {len(excel_journals)} unique Journals in Excel.")
    print(f"Found {len(excel_accounts)} unique Accounts in Excel.")

    # 2. Connect to Odoo 19
    print("\nConnecting to Odoo 19...")
    client = OdooJsonRpcClient(args.dest_url, args.dest_db, args.dest_user, args.dest_password)
    if not client.authenticate():
        print("Authentication failed to Odoo 19")
        return

    # 3. Fetch Existing Journals and Accounts
    print("Fetching existing Journals and Accounts from Odoo 19...")
    
    # Journals: Search by Name
    # Normalize by stripping whitespace and uppercase for comparison
    odoo_journals = client.execute_kw('account.journal', 'search_read', [[], ['name']])
    odoo_journal_names = {j['name'].strip().upper() for j in odoo_journals}
    
    # Accounts: Search by Code and Name
    # In Excel, Account might be "Code Name" or just "Code" or "Name" depending on export.
    # Typically export uses "Code Name" or just Name.
    # Reviewing export script: `account_code = sanitize_for_excel(line.get('account_id')[1])` -> This is "Code Name" usually.
    # Odoo 19: we should check if we can match Code OR Name.
    # Let's clean the Excel Account string. Usually it's "101000 Cash".
    # extraction strategy: First word is code? Or try to match full string?
    
    odoo_accounts = client.execute_kw('account.account', 'search_read', [[], ['code', 'name']])
    # Create valid sets
    odoo_account_codes = {str(a['code']) for a in odoo_accounts}
    odoo_account_names = {a['name'].strip().upper() for a in odoo_accounts}
    odoo_account_full = {f"{a['code']} {a['name']}".strip().upper() for a in odoo_accounts}
    
    # 4. Compare
    missing_journals = []
    print("\n--- MISSING JOURNALS ---")
    for j in excel_journals:
        j_clean = str(j).strip().upper()
        if j_clean not in odoo_journal_names:
            missing_journals.append(j)
            print(f"[MISSING] {j}")

    if not missing_journals:
        print("All Journals exist in Odoo 19.")

    missing_accounts = []
    print("\n--- MISSING ACCOUNTS ---")
    for a in excel_accounts:
        a_str = str(a).strip()
        a_upper = a_str.upper()
        
        # Check Full Match "123 Name"
        if a_upper in odoo_account_full:
            continue
            
        # Check Split "123" (Code)
        parts = a_str.split(' ', 1)
        code = parts[0]
        if code in odoo_account_codes:
            continue
            
        # Check Name Match (if no code)
        # Assuming if it doesn't start with digit, it might be just name
        if a_upper in odoo_account_names:
            continue

        missing_accounts.append(a)
        print(f"[MISSING] {a}")

    if not missing_accounts:
        print("All Accounts exist in Odoo 19.")

    # 5. Save Report
    report_file = os.path.join(args.export_dir, 'Missing_Items_Report.txt')
    with open(report_file, 'w') as f:
        f.write("MISSING ITEMS REPORT\n")
        f.write("====================\n\n")
        
        f.write("MISSING JOURNALS:\n")
        if missing_journals:
            for j in missing_journals:
                f.write(f"- {j}\n")
        else:
            f.write("None\n")
            
        f.write("\n")
        
        f.write("MISSING ACCOUNTS:\n")
        if missing_accounts:
            for a in missing_accounts:
                f.write(f"- {a}\n")
        else:
            f.write("None\n")

    print(f"\nReport saved to: {report_file}")

if __name__ == '__main__':
    main()
