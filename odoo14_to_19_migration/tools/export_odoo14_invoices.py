import json
import random
import sys
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
    # Remove characters that are not allowed in Excel (XML invalid chars)
    # Range of allowed characters: 
    # #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
    # We strip out control characters (0-8, 11-12, 14-31)
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
        try:
            response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers, timeout=300)
            return response.json()
        except Exception:
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
    parser = argparse.ArgumentParser(description='Export Odoo 14 Invoices to Excel')
    # Defaulting to localhost:8079 as per previous context for Odoo 19, 
    # BUT wait, this is requesting ODOO 14 data.
    # The user environment seems to only have Odoo 19 running locally (metro modules).
    # The migration script connects to Odoo 14 via RPC.
    # I need to use the Odoo 14 credentials from migration config or user arguments.
    # Defaulting to the same creds commonly used in migration scripts.
    parser.add_argument('--url', default='https://erpmfs.com', help='Odoo 14 URL')
    parser.add_argument('--db', default='metro_production_8_8_22', help='Odoo 14 DB')
    parser.add_argument('--user', default='Sales.auh@metrofiresystems.com', help='Odoo 14 User')
    parser.add_argument('--password', default='Sales@185734', help='Odoo 14 Password')
    parser.add_argument('--limit', type=int, default=0, help='Limit records')
    
    args = parser.parse_args()

    print("\n" + "="*80)
    print(f"EXPORTING ODOO 14 INVOICES TO EXCEL")
    print("="*80)

    # Note: We are connecting directly to Odoo 14 here? 
    # No, the provided credentials 'https://metro.equdaierp.com' are for the remote Odoo 14 server.
    # The script uses JSON-RPC to fetch data.
    
    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    
    if not client.authenticate():
        print("Authentication failed to Odoo 14!")
        sys.exit(1)

    print("Connected to Odoo 14.")

    # Fetch Invoices
    # Filter: Posted invoices? Or all? User said "generate all invoices".
    # Let's filter by type='out_invoice' and state='posted' usually desired for migration.
    domain = [('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]
    
    fields = ['name', 'partner_id', 'invoice_date', 'invoice_date_due', 'user_id', 'amount_total', 'invoice_line_ids', 'currency_id', 'branch_id', 'state', 'payment_state', 'journal_id']
    
    print("Fetching Invoice Headers...")
    
    # Try Odoo 14 standard 'move_type'
    domain = [('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]
    search_args = [domain]
    kwargs = {'limit': args.limit} if args.limit > 0 else {}
    
    invoice_ids = client.execute_kw('account.move', 'search', search_args, kwargs)
    
    # Fallback to Odoo 13 'type' if Odoo 14 specific field failed (just in case it's actually Odoo 13)
    if not invoice_ids:
        print("No invoices found with 'move_type'. Trying 'type' field (Legacy/Odoo 13)...")
        domain = [('type', '=', 'out_invoice'), ('state', '=', 'posted')]
        search_args = [domain]
        invoice_ids = client.execute_kw('account.move', 'search', search_args, kwargs)

    print(f"Found {len(invoice_ids)} invoices.")

    if not invoice_ids:
        # Debug: Check if we can see ANY moves?
        print("DEBUG: Checking if we can read ANY account.move records...")
        any_moves = client.execute_kw('account.move', 'search', [[]], {'limit': 5})
        if any_moves:
             print(f"Yes, found {len(any_moves)} random moves. IDs: {any_moves}")
             # Check one to see fields
             sample = client.execute_kw('account.move', 'read', [any_moves[:1], ['name', 'type', 'move_type', 'state']])
             print(f"Sample Record Fields: {sample}")
        else:
             print("No records found at all. Check permissions or DB.")
        return

    # Interactive Limit Request
    try:
        user_input = input(f"Enter number of invoices to export (Press Enter for all {len(invoice_ids)}): ").strip()
        if user_input:
            limit_val = int(user_input)
            if limit_val > 0 and limit_val < len(invoice_ids):
                invoice_ids = invoice_ids[:limit_val]
                print(f"Limiting export to first {len(invoice_ids)} invoices.")
    except ValueError:
        print("Invalid number. Exporting all.")
    except Exception:
        pass

    # Prepare Data List
    excel_rows = []
    
    count = 0
    total = len(invoice_ids)
    
    # Batch process
    batch_size = 50
    for i in range(0, len(invoice_ids), batch_size):
        batch_ids = invoice_ids[i:i+batch_size]
        invoices = client.execute_kw('account.move', 'read', [batch_ids, fields])
        
        for inv in invoices:
            inv_name = sanitize_for_excel(inv.get('name'))
            partner = sanitize_for_excel(inv.get('partner_id')[1]) if inv.get('partner_id') else ''
            date = inv.get('invoice_date')
            due_date = inv.get('invoice_date_due')
            sales_agent = sanitize_for_excel(inv.get('user_id')[1]) if inv.get('user_id') else ''
            total_amt = inv.get('amount_total')
            branch_name = sanitize_for_excel(inv.get('branch_id')[1]) if inv.get('branch_id') else ''
            journal_name = sanitize_for_excel(inv.get('journal_id')[1]) if inv.get('journal_id') else ''
            
            # Fetch Lines
            line_ids = inv.get('invoice_line_ids', [])
            if not line_ids:
                continue
                
            # Fetch Line details
            # Display_type=False ensures product lines (usually)
            line_fields = ['product_id', 'name', 'quantity', 'price_unit', 'tax_ids', 'price_subtotal', 'display_type', 'account_id']
            lines = client.execute_kw('account.move.line', 'read', [line_ids, line_fields])
            
            # Fetch Tax Names efficiently for this batch
            tax_ids_in_batch = set()
            for line in lines:
                tax_ids_in_batch.update(line.get('tax_ids', []))
            
            tax_map = {}
            if tax_ids_in_batch:
                taxes_data = client.execute_kw('account.tax', 'read', [list(tax_ids_in_batch), ['name']])
                for t in taxes_data:
                    tax_map[t['id']] = sanitize_for_excel(t.get('name'))
            
            first_line = True
            for line in lines:
                # Exclude notes/sections if desired? User data format has "Product" column.
                if line.get('display_type'): 
                    continue
                
                prod_name = sanitize_for_excel(line.get('product_id')[1]) if line.get('product_id') else ''
                desc = sanitize_for_excel(line.get('name'))
                qty = line.get('quantity')
                price = line.get('price_unit')
                account_code = sanitize_for_excel(line.get('account_id')[1]) if line.get('account_id') else ''

                # Map Taxes based on Branch (User Request)
                # Available: VAT AUH (AE), VAT RAK (AE), VAT DXB (AE), VAT SHJ (AE), VAT AJM (AE), VAT FUJ (AE), VAT DS
                mapped_tax_str = ''
                if line.get('tax_ids'):
                    # Default raw names
                    raw_tax_names = [tax_map.get(tid, '') for tid in line.get('tax_ids', [])]
                    
                    # Heuristic Mapping based on Branch
                    b_name_upper = str(branch_name).upper()
                    new_tax_name = None
                    
                    if 'ABU DHABI' in b_name_upper or 'AUH' in b_name_upper:
                        new_tax_name = 'VAT AUH (AE)'
                    elif 'DUBAI' in b_name_upper or 'DXB' in b_name_upper:
                        new_tax_name = 'VAT DXB (AE)'
                    elif 'SHARJAH' in b_name_upper or 'SHJ' in b_name_upper:
                        new_tax_name = 'VAT SHJ (AE)'
                    elif 'AJMAN' in b_name_upper or 'AJM' in b_name_upper:
                        new_tax_name = 'VAT AJM (AE)'
                    elif 'RAS' in b_name_upper or 'RAK' in b_name_upper:
                        new_tax_name = 'VAT RAK (AE)'
                    elif 'FUJAIRAH' in b_name_upper or 'FUJ' in b_name_upper:
                        new_tax_name = 'VAT FUJ (AE)'
                    
                    # If we found a mapping and there IS a tax on the line, force the mapped name.
                    # Assumption: Only one VAT tax usually.
                    if new_tax_name:
                         mapped_tax_str = new_tax_name
                    else:
                         mapped_tax_str = ', '.join(filter(None, raw_tax_names))
                else:
                    mapped_tax_str = ''

                row = {
                    'Number': inv_name if first_line else None,
                    'Partner': partner if first_line else None,
                    'Branch': branch_name if first_line else None,
                    'Journal*': journal_name if first_line else None,
                    'Invoice Bill Date': date if first_line else None,
                    'Due Date': due_date if first_line else None,
                    'Sale Agent': sales_agent if first_line else None,
                    'Invoice Lines/Product': prod_name,
                    'Description': desc,
                    'Invoice Lines/Quantity': qty,
                    'Invoice Lines/Unit Price': price,
                    'Invoice Lines/Taxes': mapped_tax_str,
                    'Invoice Lines/Account*': account_code
                }
                excel_rows.append(row)
                first_line = False
        
        count += len(batch_ids)
        print(f"Processed {count}/{total} invoices...", end='\r')

    print("\nWriting to Excel...")
    df = pd.DataFrame(excel_rows)
    
    # Reorder columns to match format
    cols = ['Number', 'Partner', 'Branch', 'Journal*', 'Invoice Bill Date', 'Due Date', 'Sale Agent', 
            'Invoice Lines/Product', 'Description', 'Invoice Lines/Quantity', 'Invoice Lines/Unit Price', 
            'Invoice Lines/Taxes', 'Invoice Lines/Account*']
            
    # Ensure they exist (if DataFrame has unexpected cols)
    for c in cols:
        if c not in df.columns:
            df[c] = None
            
    df = df[cols]
    
    df = df[cols]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'Odoo14_Exported_Invoices_{timestamp}.xlsx'
    
    try:
        df.to_excel(output_file, index=False)
        print(f"Successfully exported to {output_file}")
    except PermissionError:
        print(f"ERROR: Could not write to {output_file}. Is the file open?")
        print("Trying with a new name...")
        output_file = f'Odoo14_Exported_Invoices_{timestamp}_new.xlsx'
        df.to_excel(output_file, index=False)
        print(f"Successfully exported to {output_file}")

if __name__ == '__main__':
    main()
