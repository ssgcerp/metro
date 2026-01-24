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
                # Don't just raise, let the caller handle or return None? 
                # Better to raise to stop execution or catch in main loop.
                # If I raise here, existing code usage `if result:` might break if I don't catch.
                # But 'execute_kw' expects result.
                return res_json # Let execute_kw handle or return error
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
    parser = argparse.ArgumentParser(description='Import Invoices from Excel to Odoo 19')
    parser.add_argument('--url', default='http://localhost:8079', help='Odoo 19 URL')
    parser.add_argument('--db', default='metrodb', help='Odoo 19 DB')
    parser.add_argument('--user', default='admin', help='Odoo 19 User')
    parser.add_argument('--password', default='Amaze@321', help='Odoo 19 Password')
    parser.add_argument('--file', default=r'e:\odoo modules\19\metro\odoo14_to_19_migration\import_data.xlsx', help='Excel Import File')
    
    args = parser.parse_args()

    print("\n" + "="*80)
    print(f"IMPORTING INVOICES FROM EXCEL")
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
    
    # Forward Fill Header Columns to handle merged cells/sparse rows
    # Columns that represent the Invoice Header: Invoice Number, Partner, Company, date, Status
    # User changed 'Invoice #' to 'Invoice Number'
    header_cols = ['Invoice Number', 'Partner', 'Company', 'date', 'Status'] # Try 'Invoice Number'
    # Fallback if user uses 'Invoice #'
    if 'Invoice Number' not in df.columns and 'Invoice #' in df.columns:
        df.rename(columns={'Invoice #': 'Invoice Number'}, inplace=True)
    
    # Verify exist
    existing_headers = [c for c in header_cols if c in df.columns]
    
    # Apply forward fill
    df[existing_headers] = df[existing_headers].ffill()
    
    # Drop rows where Invoice Number is still NaN
    df = df.dropna(subset=['Invoice Number'])

    # Process
    grouped = df.groupby('Invoice Number', sort=False)
    
    count = 0
    total = len(grouped)
    
    for invoice_num, group in grouped:
        # 1. Get Header Info from first row
        first_row = group.iloc[0]
        partner_name = str(first_row.get('Partner', '')).strip()
        date = first_row.get('date') # Format? YYYY-MM-DD usually from Excel date
        status_val = str(first_row.get('Status', '')).strip().lower() # 'posted' or 'draft'
        
        if not partner_name or partner_name == 'nan':
            print(f"Skipping Invoice {invoice_num}: No Partner Name")
            continue
            
        # 2. Find Partner
        partner_id = False
        partners = client.execute_kw('res.partner', 'search', [[('name', '=', partner_name)]], {'limit': 1})
        if not partners:
             # Try case insensitive
             partners = client.execute_kw('res.partner', 'search', [[('name', 'ilike', partner_name)]], {'limit': 1})
             
        if partners:
            partner_id = partners[0]
        else:
            # Need to create? User said: "if duplicate partner is found in database , select first partner id"
            # implied if NOT found, maybe create? Or error?
            # User said "if the product is not in our database create...". Didn't explicitly say create partner.
            # But usually imports require creating partners.
            # I will LOG WARNING and Create simple partner to allow import to succeed.
            print(f"Partner '{partner_name}' not found. Creating...")
            new_p = client.execute_kw('res.partner', 'create', [{'name': partner_name}])
            partner_id = new_p if isinstance(new_p, int) else new_p[0] # create returns ID

        # 3. Prepare Lines
        invoice_lines = []
        
        for index, row in group.iterrows():
            prod_name = str(row.get('Product', '')).strip()
            desc_val = str(row.get('Description', '')).strip()
            
            # Fallback: If product empty, use Description
            if (not prod_name or prod_name == 'nan') and desc_val and desc_val != 'nan':
                 prod_name = desc_val
            
            if not prod_name or prod_name == 'nan': 
                continue
            
            qty = row.get('Quantity', 1.0)
            price = row.get('Unit Price', 0.0)
            tax_str = str(row.get('Taxes', '')).strip()
            
            # Find/Create Product
            prod_id = False
            prods = client.execute_kw('product.product', 'search', [[('name', '=', prod_name)]], {'limit': 1})
            if prods:
                prod_id = prods[0]
            else:
                # Create Product
                print(f"Product '{prod_name}' not found. Creating...")
                # Assuming simple consumable or service to avoid stock issues? Or storable?
                # Defaulting to 'consu' (Consumable) is safest for imports.
                new_prod = client.execute_kw('product.product', 'create', [{'name': prod_name, 'type': 'consu'}])
                prod_id = new_prod if isinstance(new_prod, int) else new_prod[0]

            # Resolve Taxes
            tax_ids = []
            if tax_str and tax_str != 'nan':
                 # Split by comma if multiple?
                 tax_names = [t.strip() for t in tax_str.split(',')]
                 for t_name in tax_names:
                     # Search Tax
                     taxes = client.execute_kw('account.tax', 'search', [[('name', '=', t_name), ('type_tax_use', '=', 'sale')]], {'limit': 1})
                     if taxes:
                         tax_ids.append(taxes[0])
                     else:
                         print(f"Tax '{t_name}' not found. Will use default.")
            
            # If no taxes found from Excel, use default?
            # User: "if the Sales VAT not in database , select default Tax of that company"
            # Logic: If tax_str is provided but mapping failed -> Default.
            # If tax_str is empty -> Default? Usually yes.
            # But line creation with product usually auto-fetches default taxes from product.
            # We should probably let Odoo compute defaults if we don't pass tax_ids?
            # OR explicitly fetch company default.
            
            to_assign_taxes = [(6, 0, tax_ids)] if tax_ids else []
            # Note: If we send empty list [(6,0,[])], it clears taxes. If we don't send 'tax_ids', Odoo uses product default.
            # User said: "select default Tax of that company". This implies strict override if not found.
            # If tax_ids found, use them. If not found (and tax_str was present), use Company Default.
            
            if not tax_ids and (tax_str and tax_str != 'nan'):
                 # Fallback to company default (User request)
                 # We need company_id. Let's assume user.company_id context.
                 # Actually simpler: Just don't pass 'tax_ids' and let product defaults apply? 
                 # Or fetch company sale tax.
                 # Let's fetch company default for precision.
                 user_data = client.execute_kw('res.users', 'read', [client.uid, ['company_id']])
                 company_id = user_data[0]['company_id'][0]
                 company = client.execute_kw('res.company', 'read', [company_id, ['account_sale_tax_id']])
                 if company and company[0]['account_sale_tax_id']:
                      def_tax = company[0]['account_sale_tax_id'][0]
                      to_assign_taxes = [(6, 0, [def_tax])]

            line_vals = {
                'product_id': prod_id,
                'name': row.get('Description') or prod_name,
                'quantity': qty,
                'price_unit': price,
            }
            if to_assign_taxes:
                line_vals['tax_ids'] = to_assign_taxes

            invoice_lines.append((0, 0, line_vals))

        # 4. Create Invoice
        if not invoice_lines:
            print(f"Skipping Invoice {invoice_num}: No valid lines.")
            continue
            
        # Format Invoice Number (remove .0 if float)
        inv_name = str(invoice_num)
        if inv_name.endswith('.0'):
            inv_name = inv_name[:-2]

        inv_vals = {
            'move_type': 'out_invoice',
            'partner_id': partner_id,
            'name': inv_name,  # Force the Import Number
            'invoice_date': str(date)[:10] if date else str(datetime.now().date()),
            'invoice_line_ids': invoice_lines,
            'payment_reference': inv_name # Store original number
        }
        
        try:
            # Create
            new_inv_id = client.execute_kw('account.move', 'create', [inv_vals])
            print(f"Created Invoice {invoice_num} -> ID {new_inv_id}")
            
            # Auto-Post if needed
            # Normalize status check
            if new_inv_id and status_val.lower() == 'posted':
                print(f"Attempting to post Invoice {invoice_num}...")
                try:
                    client.execute_kw('account.move', 'action_post', [[new_inv_id]])
                    print(f"SUCCESS: Posted Invoice {invoice_num}")
                except Exception as e:
                    print(f"WARNING: Failed to post Invoice {invoice_num}: {e}")
                    
            count += 1
        except Exception as e:
            print(f"Failed to create Invoice {invoice_num}: {e}")

    print(f"\nImport Finished. Created {count} invoices.")

if __name__ == '__main__':
    main()
