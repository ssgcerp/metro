
import json
import random
import sys
import datetime
import requests
import argparse
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(message)s', 
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler("fix_bill_debug.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
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
                # print(f"\nRPC ERROR: {res_json['error']}\n") 
                return res_json # Let caller handle
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
        # Ensure context is preserved or added
        # Most Odoo calls rely on kwargs['context'] for context
        params = {"model": model, "method": method, "args": args, "kwargs": kwargs}
        result = self.json_rpc("/web/dataset/call_kw", params)
        if hasattr(result, 'get_result'):
             return result.get_result()
        if 'error' in result:
            return result # Return the error dict
        return result.get('result')

def main():
    parser = argparse.ArgumentParser(description='Fix Bill Company in Odoo 19')
    parser.add_argument('--url', required=True, help='Odoo URL')
    parser.add_argument('--db', required=True, help='Odoo DB')
    parser.add_argument('--user', required=True, help='Odoo User')
    parser.add_argument('--password', required=True, help='Odoo Password')
    
    # Made optional for interactive mode
    parser.add_argument('--old-company', help='Current Company Name (e.g. SHARJAH)')
    parser.add_argument('--new-company', help='Correct Company Name (e.g. DUBAI)')
    parser.add_argument('--bills', help='Comma-separated list of bills')
    parser.add_argument('--default-tax', help='Default Purchase Tax Name (e.g. VAT 5 Percent)')
    
    args = parser.parse_args()

    print("\n" + "="*80)
    print("FIXING BILL COMPANIES (Interactive Mode)")
    print("="*80)

    # 1. Connect
    client = OdooJsonRpcClient(args.url, args.db, args.user, args.password)
    if not client.authenticate():
        print("Authentication failed!")
        sys.exit(1)
    print("Connected to Odoo 19.")

    # 1.5 Setup Universal Context (See all companies)
    print("Fetching all companies to setup access rights...")
    all_companies = client.execute_kw('res.company', 'search_read', [[], ['id', 'name']])
    all_company_ids = [c['id'] for c in all_companies]
    print(f"Enabled access to {len(all_company_ids)} companies: {[c['name'] for c in all_companies]}")
    
    # We will pass this context to every call to ensure we can see/edit records in any company
    # In JSON-RPC calls via 'call_kw', context usually goes inside kwargs.
    universal_context = {'allowed_company_ids': all_company_ids}

    # ---------------------------------------------------------
    # STEP 1: Get Bill Numbers
    # ---------------------------------------------------------
    targets = []
    if args.bills:
        targets = [b.strip() for b in args.bills.split(',') if b.strip()]
    
    if not targets:
        print("\n[STEP 1] Enter Bill Numbers (comma separated):")
        print("(Paste your list and press Enter)")
        inp = input("> ")
        targets = [b.strip() for b in inp.split(',') if b.strip()]
    
    if not targets:
        print("No bills provided. Exiting.")
        sys.exit(0)

    # ---------------------------------------------------------
    # STEP 2: Current Company Name
    # ---------------------------------------------------------
    old_company_name = args.old_company
    if not old_company_name:
        print("\n[STEP 2] Enter Current (OLD) Company Name (e.g. SHARJAH):")
        old_company_name = input("> ").strip()
    
    if not old_company_name:
        print("Old company name required. Exiting.")
        sys.exit(1)

    # ---------------------------------------------------------
    # STEP 3: Correct Company Name
    # ---------------------------------------------------------
    new_company_name = args.new_company
    if not new_company_name:
        print("\n[STEP 3] Enter Correct (NEW) Company Name (e.g. DUBAI):")
        new_company_name = input("> ").strip()

    if not new_company_name:
        print("New company name required. Exiting.")
        sys.exit(1)
        
    print("\n" + "-"*60)
    print(f"Goal: Move {len(targets)} Bills")
    print(f"From: {old_company_name}")
    print(f"To:   {new_company_name}")
    print("-"*60)

    # Resolve Company IDs
    # New Company
    new_comp_data = client.execute_kw('res.company', 'search_read', 
                                     [[('name', 'ilike', new_company_name)]], 
                                     {'fields': ['id', 'name'], 'limit': 1, 'context': universal_context})
    if not new_comp_data:
        print(f"ERROR: Could not find New Company '{new_company_name}' in Odoo.")
        sys.exit(1)
    new_company_id = new_comp_data[0]['id']
    new_company_real_name = new_comp_data[0]['name']
    
    # [STEP 4] Default Tax (Optional)
    default_tax_name = args.default_tax
    if not default_tax_name and not args.bills:
        default_tax_name = input("\n[STEP 4] Enter Default Purchase TAX Name (e.g. 'VAT 5%') [Optional - Press Enter to skip]: ").strip()
    
    # Pre-fetch a valid Journal for the new company
    # We need a 'purchase' journal to allow the move of a Vendor Bill
    journal_domain = [('type', '=', 'purchase'), ('company_id', '=', new_company_id)]
    target_journal_data = client.execute_kw('account.journal', 'search_read', [journal_domain], 
                                           {'fields': ['id', 'name'], 'limit': 1, 'context': universal_context})
    
    if not target_journal_data:
        print(f"ERROR: No 'Purchase' Journal found in company '{new_company_real_name}'. Cannot move bills.")
        sys.exit(1)
    
    target_journal_id = target_journal_data[0]['id']
    target_journal_name = target_journal_data[0]['name']
    print(f"Target Journal: {target_journal_name} (ID: {target_journal_id})")
    
    # Resolve Default Tax ID if provided
    default_tax_id = None
    if default_tax_name:
        dtax_data = client.execute_kw('account.tax', 'search_read', 
                                      [[('company_id', '=', new_company_id), ('name', 'ilike', default_tax_name), ('type_tax_use', '=', 'purchase')]], 
                                      {'fields': ['id', 'name'], 'limit': 1, 'context': universal_context})
        if dtax_data:
            default_tax_id = dtax_data[0]['id']
            print(f"Default Tax Resolved: {dtax_data[0]['name']} (ID: {default_tax_id})")
        else:
            print(f"WARNING: Could not find tax '{default_tax_name}' in new company. Fallback DISABLED.")
    
    # Old Company (Optional check)
    old_comp_data = client.execute_kw('res.company', 'search_read', 
                                     [[('name', 'ilike', old_company_name)]], 
                                     {'fields': ['id', 'name'], 'limit': 1, 'context': universal_context})
    old_company_id = old_comp_data[0]['id'] if old_comp_data else None

    # ---------------------------------------------------------
    # PRE-CACHE Accounts and Taxes for New Company
    # ---------------------------------------------------------
    print("Caching Accounts and Taxes for target company...")
    
    # Cache Accounts: Code -> ID
    # account.account uses company_ids (M2M) or company_id?
    # Inspector showed 'company_ids'. So we check if new_company_id is IN company_ids.
    new_accounts_data = client.execute_kw('account.account', 'search_read', 
                                         [[('company_ids', 'in', [new_company_id])]], 
                                         {'fields': ['id', 'code'], 'context': universal_context})
    if isinstance(new_accounts_data, dict): new_accounts_data = [] # Safety
    account_map = {a['code']: a['id'] for a in new_accounts_data}
    
    # Cache Taxes: Name -> ID
    new_taxes_data = client.execute_kw('account.tax', 'search_read', 
                                      [[('company_id', '=', new_company_id), ('type_tax_use', '=', 'purchase')]], 
                                      {'fields': ['id', 'name'], 'context': universal_context})
    if isinstance(new_taxes_data, dict): new_taxes_data = [] # Safety
    tax_map = {t['name']: t['id'] for t in new_taxes_data}

    # ---------------------------------------------------------
    # LOOP: Step 4 -> Step 7
    # ---------------------------------------------------------
    success_count = 0
    fail_count = 0

    for bill_ref in targets:
        print(f"\n[Processing] {bill_ref}")
        
        # Step A: Find Bill (Robust Search)
        domain = [('name', '=', bill_ref)]
        bill_data = client.execute_kw('account.move', 'search_read', [domain], 
                                      {'fields': ['id', 'state', 'company_id', 'move_type', 'ref', 'name'], 'context': universal_context})
        # ... fallback searches ...
        if not bill_data:
             domain = [('name', '=ilike', bill_ref.strip())]
             bill_data = client.execute_kw('account.move', 'search_read', [domain], 
                                      {'fields': ['id', 'state', 'company_id', 'move_type', 'ref', 'name'], 'context': universal_context})
        if not bill_data:
             domain = [('ref', '=', bill_ref)]
             bill_data = client.execute_kw('account.move', 'search_read', [domain], 
                                      {'fields': ['id', 'state', 'company_id', 'move_type', 'ref', 'name'], 'context': universal_context})

        if not bill_data:
            print(f"  -> ERROR: Bill not found.")
            fail_count += 1
            continue
        
        target_bill = None
        for b in bill_data:
            if b['move_type'] == 'in_invoice':
                target_bill = b
                break
        
        if not target_bill:
             print(f"  -> ERROR: Found record but not in_invoice.")
             fail_count += 1
             continue
             
        bill = target_bill
        bill_id = bill['id']
        curr_state = bill['state']
        curr_comp_id = bill['company_id'][0] if bill['company_id'] else -1
        original_name = bill['name'] # Save this if we want to restore (optional)

        if curr_comp_id == new_company_id:
            print(f"  -> Already in correct company. Skipping.")
            continue

        try:
            # STEP 4: Draft
            if curr_state == 'posted':
                print("  -> (Step 4) Setting to Draft...")
                draft_res = client.execute_kw('account.move', 'button_draft', [[bill_id]], {'context': universal_context})
                if isinstance(draft_res, dict) and 'error' in draft_res:
                     print(f"     [Error] Draft Failed: {draft_res['error']['data']['message']}")
                     fail_count += 1
                     continue

            # STEP 4.5: Fix Partner Company Inconsistency
            # If the partner is tied to a specific company that is NOT the new company,
            # we must make it shared (company_id = False) or match the new company.
            bill_p_info = client.execute_kw('account.move', 'read', [[bill_id]], {'fields': ['partner_id'], 'context': universal_context})
            if bill_p_info and bill_p_info[0].get('partner_id'):
                p_id_raw = bill_p_info[0]['partner_id']
                # p_id_raw is [id, name]
                pid = p_id_raw[0]
                p_name = p_id_raw[1]
                
                # Check Partner's Company
                p_data = client.execute_kw('res.partner', 'read', [[pid]], {'fields': ['company_id'], 'context': universal_context})
                if p_data:
                    p_comp_id = p_data[0]['company_id'][0] if p_data[0]['company_id'] else False
                    
                    if p_comp_id and p_comp_id != new_company_id:
                         print(f"     [Warning] Partner '{p_name}' belongs to Company ID {p_comp_id}. Target is {new_company_id}.")
                         print(f"     [Fix] Removing company restriction from Partner '{p_name}' (Making Shared)...")
                         
                         res_p_write = client.execute_kw('res.partner', 'write', [[pid], {'company_id': False}], {'context': universal_context})
                         if isinstance(res_p_write, dict) and 'error' in res_p_write:
                             print(f"     [Error] Could not update partner: {res_p_write['error']['data']['message']}")
                         else:
                             print(f"     [Success] Partner company restriction removed.")

            # PRE-STEP: Cache original tax information for product lines
            original_line_taxes = {} 
            move_info_pre_clear = client.execute_kw('account.move', 'read', [[bill_id]], {'fields': ['line_ids', 'invoice_date_due', 'invoice_date'], 'context': universal_context})
            line_ids_pre_clear = move_info_pre_clear[0]['line_ids']
            
            # Get Bill Due Date (Fallback for Payable Lines)
            invoice_date = move_info_pre_clear[0]['invoice_date']
            invoice_date_due = move_info_pre_clear[0]['invoice_date_due']
            
            bill_due_date = invoice_date_due or invoice_date
            if not bill_due_date:
                bill_due_date = str(datetime.date.today())
                invoice_date = bill_due_date # Ensure Move has date too
                print(f"     [Warning] Bill has no dates! Using TODAY {bill_due_date} as fallback.")
            
            lines_data_pre_clear = client.execute_kw('account.move.line', 'read', [line_ids_pre_clear],
                                                    {'fields': ['id', 'tax_ids', 'tax_line_id', 'tax_repartition_line_id'], 'context': universal_context})

            for line_pre_clear in lines_data_pre_clear:
                if not line_pre_clear.get('tax_repartition_line_id') and not line_pre_clear.get('tax_line_id'):
                    if line_pre_clear.get('tax_ids'):
                        original_line_taxes[line_pre_clear['id']] = line_pre_clear['tax_ids']

            # STEP 4b: CLEAR TAXES
            print("  -> (Step 4b) Clearing Taxes to remove old tax lines...")
            prod_lines_with_taxes_to_clear = list(original_line_taxes.keys())
            if prod_lines_with_taxes_to_clear:
                client.execute_kw('account.move.line', 'write', [prod_lines_with_taxes_to_clear, {'tax_ids': [(6, 0, [])]}], {'context': universal_context})

            # STEP 5: Move Company & Journal (Atomic)
            print(f"  -> (Step 5) Moving Company & Journal (Atomic)...")
            
            # Ensure we read lines using the BILL'S company context to avoid multi-company obfuscation
            bill_context = universal_context.copy()
            allowed_ids = list(universal_context['allowed_company_ids']) # Copy list
            if curr_comp_id and curr_comp_id in allowed_ids:
                allowed_ids.remove(curr_comp_id)
                allowed_ids.insert(0, curr_comp_id)
            bill_context['allowed_company_ids'] = allowed_ids
            
            _logger.info(f"     [Debug] Reading lines with Active Company ID: {allowed_ids[0]}")

            move_info = client.execute_kw('account.move', 'read', [[bill_id]], {'fields': ['line_ids'], 'context': bill_context})
            line_ids = move_info[0]['line_ids']
            _logger.info(f"     [Debug] Processing Bill ID: {bill_id}, Line IDs: {line_ids}")
            lines_data = client.execute_kw('account.move.line', 'read', [line_ids], 
                                          {'fields': ['id', 'account_id', 'tax_ids', 'name', 'tax_repartition_line_id', 'tax_line_id', 'date_maturity'], 'context': bill_context})
            
            line_commands = []
            
            for line in lines_data:
                if line.get('tax_repartition_line_id') or line.get('tax_line_id'):
                    continue

                cmd_vals = {'company_id': new_company_id}
                
                # 1. Map Account & Determine Type
                target_acc_id = line.get('account_id')[0] if line.get('account_id') else False
                
                # IMPORTANT: Read Account Info using UNIVERSAL context (or New Company Context) to verify code/type? 
                # Actually, reading the OLD account info should be done with OLD company context, 
                # but reading NEW account info (fallback) needs NEW company context.
                # Let's trust target_acc_id is correct now that we used bill_context.
                
                if target_acc_id:
                    # Get info about the CURRENT account (to get code and type)
                    acc_info = client.execute_kw('account.account', 'read', [[target_acc_id]], {'fields': ['code', 'name', 'account_type'], 'context': universal_context})[0]
                    acc_code = acc_info['code']
                    acc_type = acc_info.get('account_type')
                    acc_name = acc_info.get('name')
                    
                    mapped = False
                    if acc_code and acc_code in account_map:
                        target_acc_id = account_map[acc_code]
                        cmd_vals['account_id'] = target_acc_id
                        mapped = True
                    elif acc_name:
                        # Fallback: Map by Name (e.g. "Payable")
                        # We need to search effectively. tax_map is name->id but for TAXES. We need ACCOUNT map by name.
                        # Let's search live because caching all names might be heavy? Or cache them?
                        # Let's simple search.
                        fallback_name_accs = client.execute_kw('account.account', 'search_read', 
                            [[('company_ids', 'in', [new_company_id]), ('name', '=', acc_name)]], 
                            {'fields': ['id', 'code'], 'limit': 1, 'context': universal_context})
                        
                        if fallback_name_accs:
                             target_acc_id = fallback_name_accs[0]['id']
                             cmd_vals['account_id'] = target_acc_id
                             mapped = True
                             _logger.info(f"     [Resolved] Mapped by Name '{acc_name}' to {fallback_name_accs[0]['code']}")

                    if not mapped:
                        # Fallback: Find FIRST account of same type in new company
                        _logger.info(f"     [Warning] No matching account for code '{acc_code}' or Name '{acc_name}' in new company.")
                        if acc_type:
                            # Search by Exact Type First
                            fallback_accounts = client.execute_kw('account.account', 'search_read', 
                                [[('company_ids', 'in', [new_company_id]), ('account_type', '=', acc_type)]], 
                                {'fields': ['id', 'code', 'name'], 'limit': 1, 'context': universal_context})
                            
                            # Secondary Search for 'income_other' -> 'income' (or vice versa)
                            if not fallback_accounts and acc_type == 'income_other':
                                 _logger.info("     [Info] No 'income_other' found. Trying 'income'...")
                                 fallback_accounts = client.execute_kw('account.account', 'search_read', 
                                    [[('company_ids', 'in', [new_company_id]), ('account_type', '=', 'income')]], 
                                    {'fields': ['id', 'code', 'name'], 'limit': 1, 'context': universal_context})

                            if fallback_accounts:
                                target_acc_id = fallback_accounts[0]['id']
                                cmd_vals['account_id'] = target_acc_id
                                _logger.info(f"     [Resolved] Mapped to fallback account '{fallback_accounts[0]['code']} - {fallback_accounts[0]['name']}' (Same/Similar Type: {acc_type})")
                            else:
                                _logger.info(f"     [Error] No fallback account found for type '{acc_type}'! Keeping ID {target_acc_id} (WILL FAIL).")
                        else:
                             _logger.info(f"     [Error] Could not determine account type. Keeping ID {target_acc_id} (Risky).")
                
                # Get info about the TARGET account (Type is critical for Date Maturity)
                # We need to know if the Final Account is Payable/Receivable
                if target_acc_id:
                    target_acc_info = client.execute_kw('account.account', 'read', [[target_acc_id]], {'fields': ['code', 'name', 'account_type'], 'context': universal_context})
                    if target_acc_info:
                        acc_type = target_acc_info[0].get('account_type', '')
                        acc_code_debug = target_acc_info[0].get('code', '')
                        
                        # Debug Print
                        _logger.info(f"     [Debug Line {line['id']}] Acc: {acc_code_debug} (ID: {target_acc_id}), Type: {acc_type}")

                        if acc_type in ['asset_receivable', 'liability_payable']:
                            # MUST HAVE DATE
                            if line.get('date_maturity'):
                                cmd_vals['date_maturity'] = line['date_maturity']
                            else:
                                cmd_vals['date_maturity'] = bill_due_date # Use Fallback/Today
                            
                            _logger.info(f"     [Line {line['id']}] Payable/Receivable ({acc_type}). Setting Date: {cmd_vals['date_maturity']}")
                        else:
                            # MUST NOT HAVE DATE (Vice Versa rule)
                            cmd_vals['date_maturity'] = False
                            _logger.info(f"     [Line {line['id']}] Standard ({acc_type} - {acc_code_debug}). Clearing Date.")

                line_commands.append((1, line['id'], cmd_vals))
            
            # Build Main Update
            vals = {
                'company_id': new_company_id,
                'journal_id': target_journal_id,
                'name': '/', # RESET NAME
                'invoice_date': invoice_date, # Enforce Date on Move
                'invoice_date_due': bill_due_date, # Enforce Due Date on Move
                'invoice_payment_term_id': False, # PREVENT AUTO-RECOMPUTE
                'line_ids': line_commands
            }
            
            # Execute Write
            _logger.info(f"     [Debug] Executing atomic write (Name reset to '/')...")
            res_write = client.execute_kw('account.move', 'write', [[bill_id], vals], {'context': universal_context})
            
            # CHECK FOR ERROR & RETRY
            if isinstance(res_write, dict) and 'error' in res_write:
                 error_msg = res_write['error']['data']['message']
                 if "Any journal item on a payable account must have a due date" in error_msg:
                     _logger.warning("     [Warning] Caught 'Payable Date' error. Retrying with Date Forced...")
                     
                     # Force date on ALL lines where we cleared it
                     new_vals = vals.copy()
                     new_lines_cmd = []
                     
                     for cmd in vals['line_ids']:
                         # cmd is (1, id, {values})
                         op, lid, values = cmd
                         new_values = values.copy()
                         
                         if 'date_maturity' in new_values and not new_values['date_maturity']:
                             new_values['date_maturity'] = bill_due_date
                             _logger.info(f"     [Retry] Forcing date on Line {lid}")
                             
                         new_lines_cmd.append((op, lid, new_values))
                     
                     new_vals['line_ids'] = new_lines_cmd
                     
                     # Retry Write
                     res_write = client.execute_kw('account.move', 'write', [[bill_id], new_vals], {'context': universal_context})

            if isinstance(res_write, dict) and 'error' in res_write:
                 _logger.error(f"     [Error] Write Failed: {res_write['error']['data']['message']}")
                 fail_count += 1
                 continue
            
            _logger.info(f"     [Debug] Write Success.")

            # STEP 5b: Re-apply Taxes
            print("  -> (Step 5b) Re-applying taxes...")
            lines_to_update_taxes = []
            for line_id, old_tax_ids in original_line_taxes.items():
                if not old_tax_ids:
                    continue # No taxes to re-apply

                old_taxes_data = client.execute_kw('account.tax', 'read', [old_tax_ids], {'fields': ['name'], 'context': universal_context})
                new_tax_ids = []
                for old_tax in old_taxes_data:
                    if old_tax['name'] in tax_map:
                        new_tax_ids.append(tax_map[old_tax['name']])
                    elif default_tax_id:
                        if default_tax_id not in new_tax_ids: # Avoid duplicates if multiple old taxes map to same default
                            new_tax_ids.append(default_tax_id)
                    else:
                        print(f"     [Warning] Tax '{old_tax['name']}' not found in new company. Dropping for line {line_id}.")
                
                if new_tax_ids:
                    lines_to_update_taxes.append((line_id, new_tax_ids))
                else:
                    # Ensure taxes are explicitly empty if no mapping found
                    lines_to_update_taxes.append((line_id, []))

            if lines_to_update_taxes:
                for line_id, new_taxes_for_line in lines_to_update_taxes:
                    client.execute_kw('account.move.line', 'write', [[line_id], {'tax_ids': [(6, 0, new_taxes_for_line)]}], {'context': universal_context})
            
            # STEP 5c: Restore Original Name
            # Odoo might allow this now that the journal is changed?
            if original_name and original_name != '/':
                 print(f"  -> (Step 5c) Restoring Original Name: {original_name}")
                 res_restore = client.execute_kw('account.move', 'write', [[bill_id], {'name': original_name}], {'context': universal_context})
                 if isinstance(res_restore, dict) and 'error' in res_restore:
                     print(f"     [Warning] Could not restore name: {res_restore['error']['data']['message']}")
                     # Continue anyway, better to have a new name than fail? or should we stop?
                     # User said "dont change", so maybe just warn.

            # STEP 6: Post
            print("  -> (Step 6) Posting...")
            post_res = client.execute_kw('account.move', 'action_post', [[bill_id]], {'context': universal_context})
            if isinstance(post_res, dict) and 'error' in post_res:
                 print(f"     [Error] Post Failed: {post_res['error']['data']['message']}")
            
            # STEP 7: Check Result
            check_data = client.execute_kw('account.move', 'read', [[bill_id]], {'fields': ['state', 'company_id', 'name'], 'context': universal_context})
            final_state = check_data[0]['state']
            final_comp = check_data[0]['company_id'][1]
            final_name = check_data[0]['name']
            
            if final_state == 'posted' and check_data[0]['company_id'][0] == new_company_id:
                print(f"  -> (Step 7) SUCCESS: Posted in '{final_comp}' as '{final_name}'")
                success_count += 1
            else:
                 print(f"  -> (Step 7) WARNING: Ends in state '{final_state}' in '{final_comp}'.")
                 fail_count += 1

        except Exception as e:
            print(f"  -> EXCEPTION: {e}")
            fail_count += 1

    print("\n" + "="*80)
    print(f"DONE. Success: {success_count}, Failed/Skipped: {fail_count}")
    print("="*80)

if __name__ == "__main__":
    main()
