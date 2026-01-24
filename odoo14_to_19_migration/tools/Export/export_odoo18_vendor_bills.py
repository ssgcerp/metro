import json
import random
import sys
import os
import time
import requests
import argparse
import logging
import pandas as pd
from datetime import datetime
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
_logger = logging.getLogger(__name__)

# Excel Illegal Character Sanitizer
def sanitize_for_excel(value):
    if not isinstance(value, str):
        return value
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value)

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
        
        for attempt in range(3):
            try:
                response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers, timeout=300)
                return response.json()
            except Exception as e:
                print(f"RPC CALL FAILED (Attempt {attempt+1}/3): {self.url}{endpoint} - {e}")
                time.sleep(2 * (attempt + 1)) # Backoff: 2s, 4s, 6s
        
        return None

    def authenticate(self):
        # For SAAS, we might not know the DB name exactly if multiple exist, 
        # but usually providing one is required.
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
        if result is None:
             raise Exception(f"RPC Call returned None. Check network or server logs. Model: {model}, Method: {method}")
        return result.get_result() if hasattr(result, 'get_result') else result.get('result')

def main():
    parser = argparse.ArgumentParser(description='Export Odoo 18 Vendor Bills to Excel')
    parser.add_argument('--url', default='https://metro-fire-system-llc.odoo.com', help='Odoo 18 URL')
    parser.add_argument('--db', default='metro-fire-system-llc', help='Odoo 18 DB')
    parser.add_argument('--user', default='sruthi@metrofiresystems.com', help='Odoo 18 User')
    parser.add_argument('--password', default='Sruthi@321', help='Odoo 18 Password')
    parser.add_argument('--limit', type=int, default=0, help='Limit records')
    
    # Odoo 19 Args
    parser.add_argument('--url19', default='https://metro.equdaierp.com', help='Odoo 19 URL')
    parser.add_argument('--db19', default='metrodb', help='Odoo 19 DB')
    parser.add_argument('--user19', default='admin', help='Odoo 19 User')
    parser.add_argument('--pass19', default='Amaze@321', help='Odoo 19 Password')
    
    # Specific List
    parser.add_argument('--file_list', help='Path to text file with specific Bill refs to export')
    
    args = parser.parse_args()

    print("\n" + "="*80)
    print(f"EXPORTING ODOO 18 VENDOR BILLS TO EXCEL")
    print("="*80)

    # 1. Connect to Odoo 19 (Destination) to get existing bills
    # Only if NOT using file_list (if file_list is used, we assume user knows what they want)
    client19 = None
    existing_refs = set()
    
    if not args.file_list:
        client19 = OdooJsonRpcClient(args.url19, args.db19, args.user19, args.pass19)
        print(f"Connecting to Odoo 19 ({args.url19})...")
        if client19.authenticate():
            print("Connected to Odoo 19. Fetching existing Vendor Bills...")
            existing_bills = client19.execute_kw('account.move', 'search_read', 
                [[('move_type', '=', 'in_invoice')]], 
                {'fields': ['name', 'ref', 'payment_reference']})
            
            for b in existing_bills:
                if b.get('ref'): existing_refs.add(str(b['ref']).strip())
                if b.get('name'): existing_refs.add(str(b['name']).strip()) 
            
            print(f"Found {len(existing_bills)} existing bills in Odoo 19.")
        else:
            print("WARNING: Could not connect to Odoo 19. Exporting ALL bills.")
    else:
        print(f"Using File List: {args.file_list}. Skipping Odoo 19 check.")

    # 2. Connect to Odoo 18 (Source)
    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    
    if not client.authenticate():
        print("Authentication failed to Odoo 18!")
        sys.exit(1)

    print("Connected to Odoo 18.")

    # Fetch Vendor Bills
    # Default: Posted only
    domain = [('move_type', '=', 'in_invoice')]
    
    if args.file_list:
        # If specific list requested, include DRAFT bills too
        domain.append(('state', 'in', ['posted', 'draft']))
    else:
        # Default behavior: Posted only
        domain.append(('state', '=', 'posted'))
    
    # Apply File List Filter
    if args.file_list:
        try:
            with open(args.file_list, 'r') as f:
                target_refs = [l.strip() for l in f.readlines() if l.strip()]
            if target_refs:
                print(f"Filtering for {len(target_refs)} specific bills from file.")
                # Search either by Name OR Ref
                # domain: AND [ ..., OR(name in list, ref in list) ]
                domain.append('|')
                domain.append(('name', 'in', target_refs))
                domain.append(('ref', 'in', target_refs))
            else:
                print("File list is empty!")
        except Exception as e:
            print(f"Error reading file list: {e}")
            sys.exit(1)

    # Odoo 18 fields
    fields_to_check = ['name', 'ref', 'partner_id', 'invoice_date', 'invoice_date_due', 'user_id', 'amount_total', 
                       'invoice_line_ids', 'currency_id', 'state', 'payment_state', 'journal_id', 'company_id',
                       'payment_reference', 'date', 'fiscal_position_id']
    
    # Check for branch_id
    model_fields = client.execute_kw('account.move', 'fields_get', [], {'attributes': ['string']})
    has_branch = 'branch_id' in model_fields
    
    if has_branch:
        fields_to_check.append('branch_id')
    else:
        print("No 'branch_id' field. Using 'company_id' for grouping.")

    print("Fetching Bill Headers from Odoo 18...")
    
    search_args = [domain]
    kwargs = {'limit': args.limit} if args.limit > 0 else {}
    
    # Fetch
    # If not using file list, we do manual filter. If using file list, domain handles it.
    if args.file_list:
        invoice_ids = client.execute_kw('account.move', 'search', search_args, kwargs)
        print(f"Found {len(invoice_ids)} matching bills.")
        # DEBUG: Print found headers
        if invoice_ids:
             found_headers = client.execute_kw('account.move', 'read', [invoice_ids], {'fields': ['name', 'ref']})
             for fh in found_headers:
                 print(f"  -> Found: Name='{fh.get('name')}', Ref='{fh.get('ref')}'")
    else:
        invoice_ids_all = client.execute_kw('account.move', 'search_read', search_args, {'fields': ['id', 'name', 'ref']})
        print(f"Found {len(invoice_ids_all)} total vendor bills in Odoo 18.")
        
        # FILTER
        invoice_ids = []
        skipped_count = 0
        for inv in invoice_ids_all:
            ref = str(inv.get('ref', '')).strip()
            name = str(inv.get('name', '')).strip()
            
            # Check if Ref OR Name exists in 19
            if (ref and ref in existing_refs) or (name and name in existing_refs):
                skipped_count += 1
                continue
            invoice_ids.append(inv['id'])

        print(f"Filtered out {skipped_count} existing bills. Proceeding with {len(invoice_ids)} missing bills.")



    if not invoice_ids:
        return

    # Interactive Limit Request
    try:
        user_input = input(f"Enter number of bills to export (Press Enter for all {len(invoice_ids)}): ").strip()
        if user_input:
            limit_val = int(user_input)
            if limit_val > 0 and limit_val < len(invoice_ids):
                invoice_ids = invoice_ids[:limit_val]
                print(f"Limiting export to first {len(invoice_ids)} bills.")
    except ValueError:
        print("Invalid number. Exporting all.")
    except Exception:
        pass

    # Prepare Data List
    branch_rows = {}
    
    count = 0
    total = len(invoice_ids)
    
    # Batch process
    batch_size = 10
    for i in range(0, len(invoice_ids), batch_size):
        batch_ids = invoice_ids[i:i+batch_size]
        invoices = client.execute_kw('account.move', 'read', [batch_ids, fields_to_check])
        
        if not invoices:
             print(f"Skipping batch starting at {i} due to fetch failure.")
             continue
        
        for inv in invoices:
            # DEBUG
            print(f"DEBUG: Processing {inv.get('name')} (ID: {inv.get('id')}) - Lines: {len(inv.get('invoice_line_ids', []))}")
            
            internal_number = sanitize_for_excel(inv.get('name'))
            
            # Use 'ref' as Bill Reference (Vendor Bill No)
            bill_ref = sanitize_for_excel(inv.get('ref')) 
            # Payment Reference
            payment_ref = sanitize_for_excel(inv.get('payment_reference'))
            
            partner = sanitize_for_excel(inv.get('partner_id')[1]) if inv.get('partner_id') else ''
            
            inv_date = inv.get('invoice_date')
            due_date = inv.get('invoice_date_due')
            
            # Accounting Date
            accounting_date = inv.get('date')
            
            sales_agent = sanitize_for_excel(inv.get('user_id')[1]) if inv.get('user_id') else ''
            
            # Fiscal Position
            fiscal_pos = sanitize_for_excel(inv.get('fiscal_position_id')[1]) if inv.get('fiscal_position_id') else ''
            if not fiscal_pos or 'Non-UAE' in fiscal_pos:
                fiscal_pos = 'ABUDHABI'
            
            # Always use Company for grouping
            company_name = sanitize_for_excel(inv.get('company_id')[1]) if inv.get('company_id') else 'Unassigned'
            
            # Use Company Name for column mapping
            group_name = company_name 

            journal_name = sanitize_for_excel(inv.get('journal_id')[1]) if inv.get('journal_id') else ''
            
            # Fetch Lines
            line_ids = inv.get('invoice_line_ids', [])
            if not line_ids:
                # DEBUG
                print(f"  -> Skipping {internal_number} (No invoice_line_ids)")
                continue
                
            line_fields = ['product_id', 'name', 'quantity', 'price_unit', 'tax_ids', 'price_subtotal', 'display_type', 'account_id']
            lines = client.execute_kw('account.move.line', 'read', [line_ids, line_fields])
            
            if not lines:
                 print(f"  -> Skipping {internal_number} (Lines read failed)")
                 continue

            # Fetch Tax Names efficiently for this batch
            tax_ids_in_batch = set()
            for line in lines:
                tax_ids_in_batch.update(line.get('tax_ids', []))
            
            tax_map = {}
            if tax_ids_in_batch:
                taxes_data = client.execute_kw('account.tax', 'read', [list(tax_ids_in_batch), ['name']])
                if taxes_data:
                    for t in taxes_data:
                        tax_map[t['id']] = sanitize_for_excel(t.get('name'))
            
            first_line = True
            for line in lines:
                # Odoo 18: display_type can be 'product', so strictly filter out section/note
                if line.get('display_type') in ['line_section', 'line_note']: 
                    continue
                
                prod_name = sanitize_for_excel(line.get('product_id')[1]) if line.get('product_id') else ''
                desc = sanitize_for_excel(line.get('name'))
                qty = line.get('quantity')
                price = line.get('price_unit')
                account_code = sanitize_for_excel(line.get('account_id')[1]) if line.get('account_id') else ''

                # Map Taxes based on Company Name
                mapped_tax_str = ''
                if line.get('tax_ids'):
                    raw_tax_names = [tax_map.get(tid, '') for tid in line.get('tax_ids', [])]
                    
                    c_name_upper = str(company_name).upper()
                    new_tax_name = None
                    
                    if 'ABU DHABI' in c_name_upper or 'AUH' in c_name_upper:
                        new_tax_name = 'VAT AUH (AE)'
                    elif 'DUBAI' in c_name_upper or 'DXB' in c_name_upper:
                        new_tax_name = 'VAT DXB (AE)'
                    elif 'SHARJAH' in c_name_upper or 'SHJ' in c_name_upper:
                        new_tax_name = 'VAT SHJ (AE)'
                    elif 'AJMAN' in c_name_upper or 'AJM' in c_name_upper:
                        new_tax_name = 'VAT AJM (AE)'
                    elif 'RAS' in c_name_upper or 'RAK' in c_name_upper:
                        new_tax_name = 'VAT RAK (AE)'
                    elif 'FUJAIRAH' in c_name_upper or 'FUJ' in c_name_upper:
                        new_tax_name = 'VAT FUJ (AE)'
                    
                    if new_tax_name:
                         mapped_tax_str = new_tax_name
                    else:
                         mapped_tax_str = ', '.join(filter(None, raw_tax_names))
                else:
                    mapped_tax_str = ''

                row = {
                    'Number': internal_number if first_line else None,
                    'Bill Reference': bill_ref if first_line else None, # Was 'Reference'
                    'Payment Reference': payment_ref if first_line else None, # NEW
                    'Partner': partner if first_line else None,
                    'Company': company_name if first_line else None,
                    'Journal*': journal_name if first_line else None,
                    'Invoice Bill Date': inv_date if first_line else None,
                    'Accounting Date': accounting_date if first_line else None, # NEW
                    'Due Date': due_date if first_line else None,
                    'Fiscal Position': fiscal_pos if first_line else None, # NEW
                    'Sale Agent': sales_agent if first_line else None,
                    'Invoice Lines/Product': prod_name,
                    'Description': desc,
                    'Invoice Lines/Quantity': qty,
                    'Invoice Lines/Unit Price': price,
                    'Invoice Lines/Taxes': mapped_tax_str,
                    'Invoice Lines/Account*': account_code
                }
                
                if group_name not in branch_rows:
                    branch_rows[group_name] = []
                branch_rows[group_name].append(row)
                
                first_line = False
        
        count += len(batch_ids)
        print(f"Processed {count}/{total} bills...", end='\r')


    print(f"\nCollected {sum(len(v) for v in branch_rows.values())} rows across {len(branch_rows)} companies.")
    print("\nWriting to Excel files (Company-wise)...")
    
    # Define Export Directory (Parent of 'tools', then 'Export')
    # Current script is in odootools/migration/tools/Export/
    # We want odootools/migration/Export/
    # abspath -> tools/Export/script.py
    # dirname -> tools/Export
    # dirname -> tools
    # dirname -> migration
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    export_dir = os.path.join(base_dir, 'Export')
    
    if not os.path.exists(export_dir):
        try:
            os.makedirs(export_dir)
            print(f"Created directory: {export_dir}")
        except OSError as e:
            print(f"Error creating directory {export_dir}: {e}")
            return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cols = ['Number', 'Bill Reference', 'Payment Reference', 'Partner', 'Company', 'Journal*', 
            'Invoice Bill Date', 'Accounting Date', 'Due Date', 'Fiscal Position', 'Sale Agent', 
            'Invoice Lines/Product', 'Description', 'Invoice Lines/Quantity', 'Invoice Lines/Unit Price', 
            'Invoice Lines/Taxes', 'Invoice Lines/Account*']
            
    for company, rows in branch_rows.items():
        print(f"Exporting {len(rows)} rows for Company: {company}...")
        df = pd.DataFrame(rows)
        
        for c in cols:
            if c not in df.columns:
                df[c] = None
        df = df[cols]
        
        safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(company))
        filename = f'Odoo18_VendorBills_{safe_name}_{timestamp}.xlsx'
        output_file = os.path.join(export_dir, filename)
        
        try:
            df.to_excel(output_file, index=False)
            print(f"  -> Saved to {output_file}")
        except Exception as e:
            print(f"  -> ERROR saving {output_file}: {e}")

if __name__ == '__main__':
    main()
