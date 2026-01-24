
import json
import random
import sys
import time
import requests
import argparse
import logging
import pandas as pd
from datetime import datetime

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
        return result.get_result() if hasattr(result, 'get_result') else result.get('result')

def main():
    parser = argparse.ArgumentParser(description='Import Vendor Bills from Excel to Odoo 19')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Odoo 19 URL')
    parser.add_argument('--db', default='metrodb', help='Odoo 19 DB')
    parser.add_argument('--user', default='admin', help='Odoo 19 User')
    parser.add_argument('--password', default='Amaze@321', help='Odoo 19 Password')
    parser.add_argument('--file', required=True, help='Excel Import File')
    
    args = parser.parse_args()

    print("\n" + "="*80)
    print(f"IMPORTING VENDOR BILLS FROM {args.file}")
    print("="*80)

    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    
    if not client.authenticate():
        print("Authentication failed to Odoo 19!")
        sys.exit(1)

    print("Connected to Odoo 19.")

    try:
        df = pd.read_excel(args.file)
    except FileNotFoundError:
        print(f"File not found: {args.file}")
        sys.exit(1)

    # Clean Columns
    df.columns = df.columns.str.strip()
    
    # Required Header Columns
    header_cols = [
        'Number', 'Company', 'Partner', 'Journal*', 'Invoice Bill Date', 
        'Accounting Date', 'Due Date', 'Bill Reference'
    ]
    
    # Verify exist
    existing_headers = [c for c in header_cols if c in df.columns]
    
    # Apply forward fill for header columns
    df[existing_headers] = df[existing_headers].ffill()
    
    # Drop rows where Number is NaN or empty
    df = df.dropna(subset=['Number'])
    # Also filter out empty strings or 'nan' string values
    df = df[df['Number'].astype(str).str.strip() != '']
    df = df[df['Number'].astype(str).str.lower() != 'nan']

    # Group by Bill Number
    grouped = df.groupby('Number', sort=False)
    
    count = 0
    
    for bill_ref, group in grouped:
        # 1. Get Header Info
        first_row = group.iloc[0]
        
        company_name = str(first_row.get('Company', '')).strip()
        partner_name = str(first_row.get('Partner', '')).strip()
        journal_name = str(first_row.get('Journal*', '')).strip()
        bill_date = first_row.get('Invoice Bill Date')
        due_date = first_row.get('Due Date')
        number_val = str(first_row.get('Number', '')).strip()
        vendor_bill_ref = str(first_row.get('Bill Reference', '')).strip()
        if vendor_bill_ref == 'nan':
            vendor_bill_ref = False
        
        # DEBUG: Specific check for failing bill
        if number_val == 'EXP/2025/08/0199':
             print(f"DEBUG {number_val}: Found in loop.")
             print(f"DEBUG {number_val}: vendor_bill_ref extracted as: '{vendor_bill_ref}'")
             print(f"DEBUG {number_val}: Raw Bill Ref value: '{first_row.get('Bill Reference')}'")

        
        if not partner_name or partner_name == 'nan':
            print(f"Skipping Bill {bill_ref}: No Partner Name")
            continue

        # 2. Find Company
        company_id = False
        if company_name and company_name != 'nan':
            comps = client.execute_kw('res.company', 'search', [[('name', 'ilike', company_name)]], {'limit': 1})
            if comps:
                company_id = comps[0]
            else:
                print(f"WARNING: Company '{company_name}' not found. Using user default.")
        
        # Check for duplicate
        # Search by name OR ref to catch duplicates from previous runs where mapping might have been different
        dup_domain = [('move_type', '=', 'in_invoice'), '|', ('name', '=', bill_ref), ('ref', '=', bill_ref)]
        if company_id:
            dup_domain.append(('company_id', '=', company_id))
        
        # DEBUG
        # print(f"DEBUG: Searching Duplicate: {dup_domain}")
        
        # Simplified Check: Just checks name/ref. Only exact matches.
        # Removing company_id from domain to verify if that's the blocker.
        # We can re-add checks on the result if needed.
        simple_domain = [('move_type', '=', 'in_invoice'), '|', ('name', '=', bill_ref), ('ref', '=', bill_ref)]
        
        search_ctx = {'allowed_company_ids': [company_id]} if company_id else {}
        existing = client.execute_kw('account.move', 'search', [simple_domain], {'limit': 1, 'context': search_ctx})
        # print(f"DEBUG: Found: {existing}")
        if existing:
            print(f"Skipping Bill {bill_ref}: Already exists (ID {existing[0]}).")
            continue
        
        # 3. Find Partner
        partner_id = False
        # Fetch company_id to check for inconsistencies
        partners = client.execute_kw('res.partner', 'search_read', 
            [[('name', '=', partner_name)]], 
            {'fields': ['id', 'company_id'], 'limit': 1})
        
        if not partners:
             partners = client.execute_kw('res.partner', 'search_read', 
                [[('name', 'ilike', partner_name)]], 
                {'fields': ['id', 'company_id'], 'limit': 1})
        
        if partners:
            partner_data = partners[0]
            partner_id = partner_data['id']
            p_company_id = partner_data['company_id'][0] if partner_data['company_id'] else False
            
            # Check for Company Inconsistency
            if company_id and p_company_id and p_company_id != company_id:
                print(f"  -> Fixing Partner Company Inconsistency for '{partner_name}': {p_company_id} -> False (Shared)")
                try:
                    client.execute_kw('res.partner', 'write', [[partner_id], {'company_id': False}])
                except Exception as e:
                    print(f"  -> WARNING: Failed to update partner company: {e}")

        else:
            print(f"Partner '{partner_name}' not found. Creating...")
            # Ensure partner created in correct company if specific
            p_vals = {'name': partner_name}
            if company_id:
                p_vals['company_id'] = company_id
            res = client.execute_kw('res.partner', 'create', [p_vals])
            partner_id = res if isinstance(res, int) else res[0]

        # 4. Prepare Lines
        invoice_lines = []
        company_ctx = {'company_id': company_id} if company_id else {}
        
        # Date logic
        inv_date_str = str(bill_date)[:10] if pd.notna(bill_date) else str(datetime.now().date())
        inv_due_date_str = str(due_date)[:10] if pd.notna(due_date) else inv_date_str
        
        for index, row in group.iterrows():
            prod_name = str(row.get('Invoice Lines/Product', '')).strip()
            desc_val = str(row.get('Description', '')).strip()
            account_code = str(row.get('Invoice Lines/Account*', '')).strip()
            qty = row.get('Invoice Lines/Quantity', 1.0)
            price = row.get('Invoice Lines/Unit Price', 0.0)
            
            # Fallback desc
            if (not prod_name or prod_name == 'nan') and desc_val and desc_val != 'nan':
                 prod_name = desc_val 
            
            if not prod_name or prod_name == 'nan':
                continue

            # Find/Create Product
            prod_id = False
            # Check for exact match first
            prods = client.execute_kw('product.product', 'search', [[('name', '=', prod_name)]], {'limit': 1})
            if prods:
                prod_id = prods[0]
            else:
                # Create
                print(f"Product '{prod_name}' not found. Creating...")
                res = client.execute_kw('product.product', 'create', [{'name': prod_name, 'type': 'consu'}])
                prod_id = res if isinstance(res, int) else res[0]

            # Find Account
            account_id = False
            if account_code and account_code != 'nan':
                 code_part = account_code.split(' ')[0]
                 
                 # Using company_ids as company_id field doesn't exist on account.account in Odoo 19/Custom
                 domain = [('code', '=', code_part)]
                 if company_id:
                     domain.append(('company_ids', 'in', [company_id]))
                 
                 accs = client.execute_kw('account.account', 'search', [domain], {'limit': 1})
                 if accs:
                     account_id = accs[0]

            line_vals = {
                'product_id': prod_id,
                'name': desc_val or prod_name,
                'quantity': qty,
                'price_unit': price,
                'date_maturity': inv_due_date_str, # Use invoice due date
            }
            if account_id:
                line_vals['account_id'] = account_id

            invoice_lines.append((0, 0, line_vals))

        if not invoice_lines:
            print(f"Skipping Bill {bill_ref}: No valid lines.")
            continue

        # 5. Create Bill
        inv_vals = {
            'move_type': 'in_invoice', # Vendor Bill
            'partner_id': partner_id,
            'name': number_val, # Internal Number/Sequence from Excel 'Number'
            'ref': vendor_bill_ref or number_val, # Vendor Bill Reference from Excel 'Bill Reference'
            'payment_reference': vendor_bill_ref or number_val, # Payment Ref should match Bill Ref
            'invoice_date': inv_date_str,
            'invoice_date_due': inv_due_date_str,
            'invoice_line_ids': invoice_lines,
        }
        
        if company_id:
            inv_vals['company_id'] = company_id
            
        # Find Journal if specified
        if journal_name and journal_name != 'nan':
             j_domain = [('name', '=', journal_name), ('type', '=', 'purchase')]
             if company_id:
                 j_domain.append(('company_id', '=', company_id))
             
             journals = client.execute_kw('account.journal', 'search', [j_domain], {'limit': 1})
             if journals:
                 inv_vals['journal_id'] = journals[0]
        
        try:
            new_inv_id = client.execute_kw('account.move', 'create', [inv_vals])
            print(f"Created Bill {bill_ref} -> ID {new_inv_id} (Company: {company_name})")
            count += 1
        except Exception as e:
            print(f"Failed to create Bill {bill_ref}: {e}")

    print(f"\nImport Finished. Created {count} bills.")

if __name__ == '__main__':
    main()
