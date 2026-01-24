
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
        if hasattr(result, 'get_result'):
             return result.get_result()
        return result.get('result')

def main():
    parser = argparse.ArgumentParser(description='Export Vendor Payments from Odoo 18')
    parser.add_argument('--url', required=True, help='Odoo URL')
    parser.add_argument('--db', required=True, help='Odoo DB')
    parser.add_argument('--user', required=True, help='Odoo User')
    parser.add_argument('--password', required=True, help='Odoo Password')
    parser.add_argument('--output', default='VendorPayments_Export.xlsx', help='Output Excel File')
    
    args = parser.parse_args()

    print("\n" + "="*80)
    print(f"EXPORTING VENDOR PAYMENTS FROM {args.url} ({args.db})")
    print("="*80)

    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    
    if not client.authenticate():
        print("Authentication failed to Odoo!")
        sys.exit(1)

    print("Connected to Odoo.")

    # Search for Vendor Payments
    # partner_type = 'supplier'
    # payment_type = 'outbound' (Paying vendor) or 'inbound' (Refund from vendor) - Usually we want outbound
    # state != 'cancel' (optional, or maybe we want all)
    
    domain = [
        ('partner_type', '=', 'supplier'),
        ('state', '!=', 'cancel') # Skip cancelled payments? User asked for all fields, usually implies valid ones.
    ]
    
    # Fields to fetch
    # check reconciled_bill_ids (Odoo 14+) - might be reconciled_invoice_ids
    # We will try to fetch both and see which one has data logic
    
    fields = [
        'name', 'date', 'partner_id', 'amount', 'currency_id', 
        'journal_id', 'payment_method_id', 'memo', 'state', 'create_date',
        'reconciled_bill_ids', 'reconciled_invoice_ids'
    ]
    
    # Check if model has these fields first? No, execute_kw usually ignores extra fields or errors if not found.
    # Safe bet is to fetch IDs then read.
    
    print("Fetching Payment Records...")
    try:
        payment_ids = client.execute_kw('account.payment', 'search', [domain])
        print(f"Found {len(payment_ids)} payments.")
    except Exception as e:
        print(f"Error searching payments: {e}")
        sys.exit(1)

    if not payment_ids:
        print("No payments found.")
        sys.exit(0)

    # Read in chunks to avoid memory/timeout issues
    chunk_size = 500
    all_data = []
    
    # To resolve bill names efficiently, collect all bill IDs
    all_bill_ids = set()
    
    for i in range(0, len(payment_ids), chunk_size):
        chunk = payment_ids[i:i+chunk_size]
        print(f"Processing chunk {i}-{i+len(chunk)}...")
        
        try:
             records = client.execute_kw('account.payment', 'read', [chunk, fields])
             
             for rec in records:
                 # Clean up m2o
                 rec['partner_name'] = rec['partner_id'][1] if rec.get('partner_id') else ''
                 rec['journal_name'] = rec['journal_id'][1] if rec.get('journal_id') else ''
                 rec['currency_name'] = rec['currency_id'][1] if rec.get('currency_id') else ''
                 rec['payment_method'] = rec['payment_method_id'][1] if rec.get('payment_method_id') else ''
                 
                 # Linked Bills
                 # Try reconciled_bill_ids first, then reconciled_invoice_ids
                 bill_ids = []
                 if rec.get('reconciled_bill_ids'):
                     bill_ids = rec['reconciled_bill_ids']
                 elif rec.get('reconciled_invoice_ids'):
                     bill_ids = rec['reconciled_invoice_ids']
                 
                 rec['linked_bill_ids'] = bill_ids
                 all_bill_ids.update(bill_ids)
                 
                 # Prepare row
                 row = {
                     'Payment Number': rec.get('name'),
                     'Date': rec.get('date'),
                     'Partner': rec['partner_name'],
                     'Amount': rec.get('amount'),
                     'Currency': rec['currency_name'],
                     'Journal': rec['journal_name'],
                     'Payment Method': rec['payment_method'],
                     'Memo/Ref': rec.get('memo'),
                     'State': rec.get('state'),
                     'Create Date': rec.get('create_date'),
                     '_linked_bill_ids': bill_ids # Temporary store for post-processing
                 }
                 all_data.append(row)
                 
        except Exception as e:
            print(f"Error reading chunk: {e}")
            continue

    # Fetch Bill Names
    bill_map = {}
    if all_bill_ids:
        print(f"Fetching names for {len(all_bill_ids)} linked bills...")
        list_bill_ids = list(all_bill_ids)
        # Process in chunks
        for i in range(0, len(list_bill_ids), chunk_size):
             b_chunk = list_bill_ids[i:i+chunk_size]
             # account.move is the model for invoices/bills
             b_recs = client.execute_kw('account.move', 'read', [b_chunk, ['name', 'ref']])
             if b_recs:
                 for b in b_recs:
                     # Format: "Number (Ref)" or just Number? User asked for Linked Vendor Bill Number.
                     # Usually the internal number (Name) is what we link.
                     bill_map[b['id']] = b.get('name', '')
                     
    # Map back to data
    print("Mapping linked bills to payments...")
    final_rows = []
    for row in all_data:
        b_ids = row.pop('_linked_bill_ids', [])
        b_names = [bill_map.get(bid, str(bid)) for bid in b_ids]
        row['Linked Bill Numbers'] = ", ".join(b_names)
        final_rows.append(row)
        
    # DataFrame
    df = pd.DataFrame(final_rows)
    
    # Save
    print(f"Saving to {args.output}...")
    df.to_excel(args.output, index=False)
    print("Done.")

if __name__ == "__main__":
    main()
