
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
    parser = argparse.ArgumentParser(description='Import Vendor Payments to Odoo 19')
    parser.add_argument('--url', required=True, help='Odoo URL')
    parser.add_argument('--db', required=True, help='Odoo DB')
    parser.add_argument('--user', required=True, help='Odoo User')
    parser.add_argument('--password', required=True, help='Odoo Password')
    parser.add_argument('--file', required=True, help='Excel Import File')
    
    args = parser.parse_args()

    print("\n" + "="*80)
    print(f"IMPORTING VENDOR PAYMENTS TO {args.url} ({args.db})")
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
    
    print(f"Columns: {df.columns.tolist()}")
    
    # Filter for Posted only ? User said "don't upload draft"
    # Assuming 'State' column exists and contains 'posted' or 'draft'
    if 'State' in df.columns:
        print("Filtering for 'posted' ('paid', 'in_process') payments...")
        # 'paid' usually means fully reconciled, 'in_process'/ 'posted' means posted but maybe not fully reconciled or in payment run
        # We want everything except draft and cancel
        df = df[df['State'].isin(['paid', 'in_process', 'posted'])]
    else:
        print("WARNING: 'State' column not found, ignoring draft check.")
        
    count = 0
    skipped = 0
    missing_journals = set()
    
    for _, row in df.iterrows():
        try:
            # 1. Parse Bill Numbers to find Company
            bill_nums_raw = str(row.get('Linked Bill Numbers', ''))
            bill_names = [b.strip() for b in bill_nums_raw.split(',') if b.strip() and b.lower() != 'nan']
            
            company_id = False
            bill_ids = []
            
            if bill_names:
                # Search for these bills to get company
                # Using 'name' (Internal Reference) as that's what we exported
                b_domain = [('move_type', '=', 'in_invoice'), ('name', 'in', bill_names)]
                # Search ALL matching bills
                found_bills = client.execute_kw('account.move', 'search_read', [b_domain], {'fields': ['id', 'company_id', 'state', 'payment_state', 'name']})
                
                if found_bills:
                    # STRICT CHECK: All linked bills must belong to the SAME company
                    found_companies = set()
                    for b in found_bills:
                        # Safety check: b['company_id'] can be False or [id, name]
                        if b.get('company_id'):
                            found_companies.add(b['company_id'][0])
                    
                    if len(found_companies) > 1:
                         print(f"SKIPPING Payment {row.get('Payment Number')}: Linked bills belong to DIFFERENT companies {found_companies}. Cannot safely assign payment.")
                         skipped += 1
                         continue
                    
                    if len(found_companies) == 1:
                        company_id = list(found_companies)[0]
                        # Verify we found ALL bills? Not strictly necessary, but good to know.
                        bill_ids = [b['id'] for b in found_bills]
                        # print(f"  -> Determined Company {company_id} from {len(found_bills)} bills.")
                    else:
                        print(f"WARNING: Linked bills found buf have no company?? {found_bills}")
                else:
                    print(f"WARNING: Linked bills {bill_names} not found in Odoo. Cannot determine Company securely.")
                    # Do NOT fallback to Journal if bills were expected but missing. risky.
                    print(f"SKIPPING Payment {row.get('Payment Number')}: Linked bills missing.")
                    skipped += 1
                    continue
            
            # Resolve Partner early to help with Company fallback
            partner_name = str(row.get('Partner', '')).strip()
            partner_id = False
            partner_data = None
            if partner_name:
                p_dom = ['|', ('name', '=', partner_name), ('name', 'ilike', partner_name)]
                # Search including company_id field to use for disambiguation
                parts = client.execute_kw('res.partner', 'search_read', [p_dom], {'fields': ['id', 'company_id'], 'limit': 1})
                if parts: 
                    partner_data = parts[0]
                    partner_id = partner_data['id']

            if not company_id:
                # Fallback: Try to determine company from Journal Name
                # ONLY if no bills were linked in Excel (pure payment)
                if bill_names:
                     print(f"SKIPPING Payment {row.get('Payment Number')}: Has linked bills in Excel but resolution failed. Not falling back to Journal.")
                     skipped += 1
                     continue

                journal_name_raw = str(row.get('Journal', '')).strip()
                if journal_name_raw:
                    # Search journals by name
                    j_possible = client.execute_kw('account.journal', 'search_read', [[('name', '=', journal_name_raw)]], {'fields': ['company_id']})
                    
                    if j_possible:
                        # Check possible companies
                        c_entries = [j['company_id'] for j in j_possible if j['company_id']]
                        c_ids = set(c[0] for c in c_entries)
                        
                        if len(c_ids) == 1:
                            # Unique company found
                            company_id = list(c_ids)[0]
                            company_name = c_entries[0][1]
                            print(f"  -> Resolved Company '{company_name}' (Journal Unique)")
                        elif len(c_ids) > 1 and partner_data and partner_data.get('company_id'):
                            # Journal exists in multiple companies (e.g. Bank).
                            # Check if PARTNER belongs to one of these companies.
                            p_co_id = partner_data['company_id'][0]
                            if p_co_id in c_ids:
                                company_id = p_co_id
                                print(f"  -> Resolved Company ID {company_id} (Ambiguous Journal '{journal_name_raw}' matched with Partner Company)")
                            else:
                                print(f"Skipping Payment {row.get('Payment Number')}: Journal '{journal_name_raw}' in {c_ids}, but Partner Company {p_co_id} mismatch.")
                                if journal_name_raw: missing_journals.add(journal_name_raw)
                                skipped += 1
                                continue
                        else:
                             print(f"Skipping Payment {row.get('Payment Number')}: Journal '{journal_name_raw}' found in multiple companies {c_ids}. Partner fallback failed (Partner Co: {partner_data.get('company_id') if partner_data else 'None'}).")
                             if journal_name_raw: missing_journals.add(journal_name_raw)
                             skipped += 1
                             continue
                    else:
                        print(f"Skipping Payment {row.get('Payment Number')}: Journal '{journal_name_raw}' not found to infer company.")
                        if journal_name_raw: missing_journals.add(journal_name_raw)
                        skipped += 1
                        continue
                else:
                    print(f"Skipping Payment {row.get('Payment Number')}: No linked bills and No Journal name to infer company.")
                    skipped += 1
                    continue
                
            # 2. Get Data
            pay_num = row.get('Payment Number') # For Logging/Reference (Odoo will generate new name)
            
            # CHECK IF EXISTS
            # We are forcing 'name' = pay_num, so check by name
            exist_pay = client.execute_kw('account.payment', 'search', [[('name', '=', pay_num)]], {'limit': 1})
            if exist_pay:
                print(f"Payment {pay_num} already exists. Skipping.")
                skipped += 1
                continue

            date = str(row.get('Date'))[:10]
            amount = float(row.get('Amount', 0.0))
            memo = str(row.get('Memo/Ref', ''))
            if memo == 'nan': memo = ''
            
            # 3. Resolve Dependencies
            
            # Partner (Already resolved above)
            if not partner_id:
                # Try resolving again if failed (unlikely if name exists, but safe to retry or just skip)
                if partner_name:
                     p_dom = ['|', ('name', '=', partner_name), ('name', 'ilike', partner_name)]
                     parts = client.execute_kw('res.partner', 'search', [p_dom], {'limit': 1})
                     if parts: partner_id = parts[0]
            
            
            if not partner_id:
                print(f"Partner '{partner_name}' not found. Skipping. (Bill: {bill_nums_raw}, Memo: {memo})")
                skipped += 1
                continue
            
            # --- PARTNER COMPANY FIX ---
            # Odoo 19 enforces strict company checks. If Partner belongs to Company A but we pay in Company B, it crashes.
            # We must detect this and fix (make partner shared)
            if partner_id and company_id:
                # Read partner company
                p_read = client.execute_kw('res.partner', 'read', [partner_id], {'fields': ['company_id']})
                if p_read and p_read[0]['company_id']:
                    p_company_id = p_read[0]['company_id'][0]
                    p_company_name = p_read[0]['company_id'][1]
                    
                    if p_company_id != company_id:
                         print(f"  -> WARNING: Partner '{partner_name}' belongs to '{p_company_name}' (ID {p_company_id}) but Payment is for Company ID {company_id}.")
                         print(f"  -> FIXING: Removing company restriction from Partner {partner_id} (Making Shared).")
                         try:
                             client.execute_kw('res.partner', 'write', [[partner_id], {'company_id': False}])
                             print("     [Fix Applied] Partner is now Shared.")
                         except Exception as e_pfix:
                             print(f"     [Fix Failed] Could not remove company from partner: {e_pfix}")
                             # It might still fail the payment create, but we try.

            # Journal
            journal_name_raw = str(row.get('Journal', '')).strip()
            journal_id = False
            
            # --- JOURNAL MAPPING TABLE ---
            # Map specific journals to new names/codes based on Target Company Name
            # We need the company name first
            target_company_name = ""
            if company_id:
                # Optimized: We might not have the name if we just have ID. Fetch it if needed or assume mapping table handles it via fuzzy matching?
                # Actually, earlier we got company_name if we inferred it. But if we got it from Bill, we only have ID.
                # Let's verify company name for mapping.
                
                # Cache company names to avoid repeated RPC
                # We can store a dict of {id: name} at global level, but for now just fetch.
                c_res = client.execute_kw('res.company', 'read', [company_id], {'fields': ['name']})
                if c_res: target_company_name = c_res[0]['name']

            mapped_journal_name = journal_name_raw
            
            if journal_name_raw == 'Office Petty Cash':
                if "FUJAIRAH" in target_company_name.upper(): mapped_journal_name = "Petty Cash - Fujairah" # Code: PCSH
                elif "RAS AL KHAIMAH" in target_company_name.upper(): mapped_journal_name = "Petty Cash - RAK" # Code: PCSH
                elif "SHARJAH" in target_company_name.upper(): mapped_journal_name = "Petty Cash - SHJ" # Code: PCSH
                elif "AJMAN" in target_company_name.upper(): mapped_journal_name = "Petty Cash - AJM" # Code: PCSH
                elif "DUBAI" in target_company_name.upper(): mapped_journal_name = "Petty Cash - DUBAI" # Code: CSH1
                elif "ABU DHABI" in target_company_name.upper(): mapped_journal_name = "Office Petty Cash" # Correct
            
            # Use mapped name
            journal_name = mapped_journal_name
            
            if journal_name:
                j_dom = [('name', '=', journal_name), ('company_id', '=', company_id)]
                journals = client.execute_kw('account.journal', 'search', [j_dom], {'limit': 1})
                if journals: 
                    journal_id = journals[0]
                elif journal_name == 'Bank': 
                    # --- GENERIC BANK FALLBACK ---
                    # If "Bank" not found (maybe named "SIB..." or "ADCB..."), find PRIMARY BANK
                    # Search for any journal of type 'bank' in this company
                    print(f"  -> Generic 'Bank' not found in '{target_company_name}'. Searching for any Bank journal...")
                    bank_journals = client.execute_kw('account.journal', 'search', [[('type', '=', 'bank'), ('company_id', '=', company_id)]], {'limit': 1})
                    if bank_journals:
                        journal_id = bank_journals[0]
                        print(f"  -> Auto-Mapped 'Bank' to ID {journal_id}")

            if not journal_id:
                print(f"Journal '{journal_name}' (Original: '{journal_name_raw}') not found for company {company_id} ({target_company_name}). Skipping. (Bill: {bill_nums_raw}, Memo: {memo})")
                if journal_name_raw: missing_journals.add(f"{journal_name_raw} (in {target_company_name})")
                skipped += 1
                continue

            # Currency
            currency_name = str(row.get('Currency', '')).strip()
            currency_id = False
            if currency_name:
                currencies = client.execute_kw('res.currency', 'search', [[('name', '=', currency_name)]], {'limit': 1})
                if currencies: currency_id = currencies[0]
            
            if not currency_id:
                 # Default company currency?
                 pass

            # Payment Method
            method_name = str(row.get('Payment Method', '')).strip()
            method_line_id = False
            
            if method_name:
                # Odoo 19/18 uses account.payment.method.line usually linked to journal
                # We need to find the line that matches the name and payment_type
                
                # Check directly on method line if we can match the name of the method
                # The name on the line might be "Manual", "Checks", etc.
                
                # Search domain on account.payment.method.line
                # We need it to be available on the selected journal
                ml_domain = [
                    ('name', 'ilike', method_name), 
                    ('payment_type', '=', 'outbound'),
                    ('journal_id', '=', journal_id)
                ]
                method_lines = client.execute_kw('account.payment.method.line', 'search', [ml_domain], {'limit': 1})
                if method_lines:
                    method_line_id = method_lines[0]
                else:
                    # Fallback: Search method itself, then find line on journal
                    m_dom = [('name', 'ilike', method_name), ('payment_type', '=', 'outbound')]
                    methods = client.execute_kw('account.payment.method', 'search', [m_dom], {'limit': 1})
                    if methods:
                        # Find line on journal for this method
                        ml_dom_2 = [('payment_method_id', '=', methods[0]), ('journal_id', '=', journal_id)]
                        ml_2 = client.execute_kw('account.payment.method.line', 'search', [ml_dom_2], {'limit': 1})
                        if ml_2:
                            method_line_id = ml_2[0]

            # 4. Create Payment
            vals = {
                'name': pay_num,  # Force/Preserve the payment number from Excel
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'partner_id': partner_id,
                'amount': amount,
                'date': date,
                'memo': memo,
                'journal_id': journal_id,
                'company_id': company_id,
            }
            if currency_id:
                vals['currency_id'] = currency_id
            
            if method_line_id:
                vals['payment_method_line_id'] = method_line_id
            # elif method_id: # Fallback if using old valid field
            #     vals['payment_method_id'] = method_id
                
            # Create
            new_pay_id = client.execute_kw('account.payment', 'create', [vals])
            print(f"Created Payment {pay_num} -> ID {new_pay_id}")
            
            # 5. Post
            try:
                client.execute_kw('account.payment', 'action_post', [new_pay_id])
            except Exception as e_post:
                print(f"  -> WARNING: Created ID {new_pay_id} but FAILED to POST: {e_post}")
                print("  -> Continuing with next record...")
                # We can't reconcile if not posted (usually), so skip reconciliation for this one
                continue
            
            # 6. Reconcile
            if bill_ids:
                # Find the 'payable' line of the Payment
                # account_type='liability_payable' (or just 'payable' in older versions, Odoo 19 uses account_type selection)
                # We search move_lines of the payment move.
                # First get the move_id of the payment
                pay_rec = client.execute_kw('account.payment', 'read', [new_pay_id, ['move_id']])
                
                if pay_rec and pay_rec[0].get('move_id'):
                     pay_move_id = pay_rec[0]['move_id'][0]
                else:
                     print(f"  -> WARNING: Payment {new_pay_id} has no move_id? Skipping reconciliation.")
                     continue
                
                # Get payment lines
                p_lines = client.execute_kw('account.move.line', 'search', [[('move_id', '=', pay_move_id), ('account_id.account_type', '=', 'liability_payable')]])
                
                # Get Bill lines (that are payable and unreconciled)
                # bill_ids are 'account.move' ids.
                # We want lines from these bills
                b_lines = client.execute_kw('account.move.line', 'search', [
                    [('move_id', 'in', bill_ids), ('account_id.account_type', '=', 'liability_payable'), ('reconciled', '=', False)]
                ])
                
                if p_lines and b_lines:
                    lines_to_rec = p_lines + b_lines
                    # Reconcile
                    # We can call 'reconcile' on the recordset
                    try:
                        client.execute_kw('account.move.line', 'reconcile', [lines_to_rec])
                        print(f"  -> Reconciled with {len(bill_ids)} bills.")
                    except Exception as re:
                        print(f"  -> Failed to reconcile: {re}")
                else:
                    print("  -> Could not find reconcileable lines (maybe already paid?).")
            
            count += 1
            
        except Exception as e:
            print(f"Error processing row {row.get('Payment Number')}: {e}")
            skipped += 1

    print("\n" + "="*80)
    print(f"Import Finished. Created: {count}, Skipped: {skipped}")
    
    if missing_journals:
        report_path = "Missing_Journals_Report.txt"
        with open(report_path, "w") as f:
            f.write("MISSING JOURNALS REPORT (Not found in Odoo 19):\n")
            f.write("=" * 50 + "\n")
            for mj in sorted(missing_journals):
                 f.write(f" - {mj}\n")
        print(f"\nMissing Journals Report saved to: {report_path}")
        
    print("="*80)

if __name__ == "__main__":
    main()
