
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
    parser = argparse.ArgumentParser(description='Report Missing Journals from Vendor Payments Excel')
    parser.add_argument('--url', required=True, help='Odoo URL')
    parser.add_argument('--db', required=True, help='Odoo DB')
    parser.add_argument('--user', required=True, help='Odoo User')
    parser.add_argument('--password', required=True, help='Odoo Password')
    parser.add_argument('--file', required=True, help='Excel Import File')
    
    args = parser.parse_args()

    print("\n" + "="*80)
    print(f"CHECKING MISSING JOURNALS: {args.file}")
    print("="*80)

    # 1. Read Excel
    try:
        df = pd.read_excel(args.file)
    except FileNotFoundError:
        print(f"File not found: {args.file}")
        sys.exit(1)

    df.columns = df.columns.str.strip()
    
    if 'Journal' not in df.columns:
        print("Error: 'Journal' column not found in Excel.")
        sys.exit(1)
        
    excel_journals = set(df['Journal'].dropna().astype(str).str.strip().unique())
    print(f"Found {len(excel_journals)} unique journals in Excel.")

    # 2. Connect to Odoo
    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    if not client.authenticate():
        print("Authentication failed to Odoo 19!")
        sys.exit(1)
    print("Connected to Odoo 19.")

    # 3. Fetch Odoo Journals (Company-Aware)
    print("Fetching Odoo Journals...")
    odoo_journals_data = client.execute_kw('account.journal', 'search_read', [[], ['name', 'company_id']])
    
    # Structure: company_name -> set of journal names
    odoo_company_journals = {}
    
    if odoo_journals_data:
        for j in odoo_journals_data:
            j_name = j['name'].strip()
            c_name = j['company_id'][1] if j['company_id'] else "Unknown"
            
            if c_name not in odoo_company_journals:
                odoo_company_journals[c_name] = set()
            odoo_company_journals[c_name].add(j_name)
            
    print(f"Loaded journals for {len(odoo_company_journals)} companies.")

    # 4. Resolve Companies for Excel Rows
    print("Resolving companies from Linked Bills in Excel...")
    
    # Extract all bill numbers first for batch fetching
    all_bills = set()
    for index, row in df.iterrows():
        bill_nums_raw = str(row.get('Linked Bill Numbers', ''))
        bills = [b.strip() for b in bill_nums_raw.split(',') if b.strip() and b.lower() != 'nan']
        all_bills.update(bills)
        
    # Batch fetch bills
    bill_company_map = {} # bill_name -> company_name
    if all_bills:
        print(f"Fetching {len(all_bills)} bills from Odoo...")
        # Chunking to avoid too long URI
        all_bills_list = list(all_bills)
        chunk_size = 1000
        for i in range(0, len(all_bills_list), chunk_size):
            chunk = all_bills_list[i:i+chunk_size]
            b_res = client.execute_kw('account.move', 'search_read', 
                                     [[('move_type', '=', 'in_invoice'), ('name', 'in', chunk)]], 
                                     {'fields': ['name', 'company_id']})
            if b_res:
                for b in b_res:
                    if b['company_id']:
                         bill_company_map[b['name']] = b['company_id'][1]
    
    # 5. Check Journals against Resolved Companies
    missing_entries = {} # company -> set of missing journals
    unknown_company_journals = set() # Journals where company couldn't be resolved
    
    print("Analyzing Excel rows...")
    for index, row in df.iterrows():
        journal_name = str(row.get('Journal', '')).strip()
        if not journal_name or journal_name.lower() == 'nan':
            continue
            
        # Resolve Company
        company_name = None
        bill_nums_raw = str(row.get('Linked Bill Numbers', ''))
        bills = [b.strip() for b in bill_nums_raw.split(',') if b.strip() and b.lower() != 'nan']
        
        for b in bills:
            if b in bill_company_map:
                company_name = bill_company_map[b]
                break
        
        if company_name:
            # Check availability
            available_journals = odoo_company_journals.get(company_name, set())
            if journal_name not in available_journals:
                if company_name not in missing_entries:
                    missing_entries[company_name] = {} # Now a dict of journal -> list of bills
                
                if journal_name not in missing_entries[company_name]:
                     missing_entries[company_name][journal_name] = []
                
                # Add the bills that led to this mismatch
                # 'bills' variable holds the clean bill numbers from current row
                if bills:
                    missing_entries[company_name][journal_name].extend(bills)
                else:
                    missing_entries[company_name][journal_name].append("(No Linked Bill? Retrieved via other means?)")
        else:
            # Could not resolve company from bills
            # Optimistic check: does it exist anywhere?
            found_anywhere = False
            for c, j_set in odoo_company_journals.items():
                if journal_name in j_set:
                    found_anywhere = True
                    break
            
            if not found_anywhere:
                unknown_company_journals.add(journal_name)

    # 6. Report
    print("\n" + "="*80)
    print("MISSING JOURNALS REPORT (Company-Wise)")
    print("="*80)
    
    has_issues = False
    
    if missing_entries:
        has_issues = True
        if unknown_company_journals:
             # Just set
             pass
        # Correctly handle missing_entries (it's a dict now)
        for company in sorted(missing_entries.keys()):
            print(f"\nBILL BELONGS TO COMPANY: {company}")
            print("-" * 60)
            for j in sorted(missing_entries[company].keys()):
                bills_list = missing_entries[company][j]
                unique_bills = sorted(list(set(bills_list)))
                
                print(f" [EXCEL JOURNAL] {j}")
                # Print sample bills
                display_bills = unique_bills[:5]
                bill_str = ", ".join(display_bills)
                if len(unique_bills) > 5:
                    bill_str += f", ... (+{len(unique_bills)-5} others)"
                
                print(f"    -> Affected Bills: {bill_str}")
                
                # Optional: Suggest if it exists in another company
                found_in = []
                for c, j_set in odoo_company_journals.items():
                    if j in j_set:
                        found_in.append(c)
                if found_in:
                    print(f"    -> ERROR: Not found in '{company}', but found in: {', '.join(found_in)}")
                else:
                    print(f"    -> ERROR: Not found in '{company}' (or any other company).")
    
    if unknown_company_journals:
        has_issues = True
        print("\n" + "="*80)
        print("JOURNALS MISSING GLOBALITY (No Company Resolved & Not found anywhere)")
        print("="*80)
        for j in sorted(unknown_company_journals):
            print(f" [MISSING] {j}")

    if not has_issues:
        print("\nGood news! All journals found in their respective companies (where applicable).")

    print("\n" + "="*80)
    print("DETAILED AFFECTED BILLS LIST")
    print("="*80)
    
    if missing_entries:
        for company in sorted(missing_entries.keys()):
            for j in sorted(missing_entries[company].keys()):
                bills_list = missing_entries[company][j]
                unique_bills = sorted(list(set(bills_list)))
                
                # Find which company this journal actually belongs to
                found_in = []
                for c, j_set in odoo_company_journals.items():
                    if j in j_set:
                        found_in.append(c)
                correct_company_str = ", ".join(found_in) if found_in else "Unknown (Not found in Odoo)"

                print(f"\n[Bill Company: {company}] -> [Journal: {j}]")
                print(f"Correct Company : {correct_company_str}")
                print(f"\nTotal Bills: {len(unique_bills)}")
                # Print all bills
                for b in unique_bills:
                    print(f" - {b}")

    print("\nDone.")

if __name__ == "__main__":
    main()
