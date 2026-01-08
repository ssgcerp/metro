import json
import random
import sys
import time
import requests
import argparse
import logging
import ssl

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
                print(f"RPC ERROR: {res_json['error']}")
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
        if result and 'error' in result:
             return None
        return result.get('result')

def get_dest_company_id(client, branch_name):
    """
    Map Odoo 14 branch_id name -> Odoo 19 company_id
    """
    if not branch_name:
        return 1

    if "ABU DHABI" in branch_name.upper():
         return 1
    
    company_ids = client.execute_kw('res.company', 'search', [[('name', 'ilike', branch_name)]], {'limit': 1})
    if company_ids:
        return company_ids[0]
        
    return 1

def mark_payment_as_cleared(client, payment_id):
    """
    Moves the OUTBOUND payment from 'In Payment' to 'Paid' by manually reconciling 
    the Outstanding Payment line with a generated Bank Clearance entry.
    """
    try:
        # Read Payment to get Move and Journal
        pay_data = client.execute_kw('account.payment', 'read', [[payment_id], ['move_id', 'journal_id', 'date', 'amount', 'currency_id', 'name']])
        if not pay_data: 
            return
        
        print(f"    DEBUG: pay_data for {payment_id}: {pay_data}")

        move_id = pay_data[0]['move_id'][0] if pay_data[0].get('move_id') else False
        journal_id = pay_data[0]['journal_id'][0] if pay_data[0].get('journal_id') else False
        payment_date = pay_data[0]['date']
        amount = pay_data[0]['amount']
        
        curr_field = pay_data[0].get('currency_id')
        currency_id = curr_field[0] if curr_field else False
        
        payment_name = pay_data[0].get('name')

        if not move_id or not journal_id:
             print("    - Missing Move or Journal. Cannot clear.")
             return

        # Find the Liquidity Line (Outstanding Payments)
        # For Outbound Payment:
        # Dr Payable
        # Cr Outstanding Payments
        # So we look for credit line that is NOT payable
        lines = client.execute_kw('account.move.line', 'search_read', 
            [[('move_id', '=', move_id), ('reconciled', '=', False), ('account_id.account_type', '!=', 'asset_receivable'), ('account_id.account_type', '!=', 'liability_payable')]],
            {'fields': ['id', 'account_id', 'debit', 'credit', 'name']}
        )
        
        if not lines:
            print("    - No outstanding liquidity line found (Maybe already Paid/Reconciled?)")
            return

        liquidity_line = lines[0]
        outstanding_account_id = liquidity_line['account_id'][0]
        
        # We need the actual Bank Account of the Journal to move money FROM.
        journal_data = client.execute_kw('account.journal', 'read', [[journal_id], ['default_account_id']])
        if not journal_data or not journal_data[0]['default_account_id']:
            print("    - Journal has no default bank account. Cannot clear.")
            return

        bank_account_id = journal_data[0]['default_account_id'][0]
        
        if bank_account_id == outstanding_account_id:
             print("    - Bank Account is same as Outstanding Account. Already Paid?")
             return

        # Create Clearance Move (Outbound)
        # Dr Outstanding Payments
        # Cr Bank
        clearance_move_vals = {
            'journal_id': journal_id,
            'date': payment_date,
            'ref': f"Clearance for {payment_name}",
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {
                    'account_id': bank_account_id,
                    'name': f"Bank Clearance - {payment_name}",
                    'debit': 0.0,
                    'credit': amount, # Cr Bank
                    'currency_id': currency_id,
                }),
                (0, 0, {
                    'account_id': outstanding_account_id,
                    'name': f"Clearance - {payment_name}",
                    'debit': amount, # Dr Outstanding
                    'credit': 0.0,
                    'currency_id': currency_id,
                })
            ]
        }
        
        clearance_move_id = client.execute_kw('account.move', 'create', [clearance_move_vals])
        client.execute_kw('account.move', 'action_post', [[clearance_move_id]])
        
        # Find the Debit line we just created in Clearance Move (to reconcile with Cr of Payment)
        clearance_lines = client.execute_kw('account.move.line', 'search_read', 
            [[('move_id', '=', clearance_move_id), ('account_id', '=', outstanding_account_id)]],
            {'fields': ['id']}
        )
        
        if clearance_lines:
            # Reconcile Payment Liquidity Line (Credit) <-> Clearance Debit Line
            client.execute_kw('account.move.line', 'reconcile', [[liquidity_line['id'], clearance_lines[0]['id']]])
            print(f"    - Payment marked as PAID (Cleared {amount} from Bank).")

    except Exception as e:
        print(f"    - Failed to mark as Paid: {e}")

def reconcile_payment(client, payment_id, partner_id):
    """
    Attempt to automatically reconcile the VENDOR payment with open BILLS
    """
    try:
        # Get Payment Lines
        payment = client.execute_kw('account.payment', 'read', [[payment_id], ['move_id', 'name', 'memo']])
        if not payment:
            return
            
        move_field = payment[0].get('move_id')
        move_id = False
        
        if move_field:
            move_id = move_field[0]
        else:
             # Fallback: Search for move by name/ref
             _logger.warning(f"  Payment {payment_id} has no move_id. Searching account.move by name...")
             payment_name = payment[0].get('name')
             move_search = client.execute_kw('account.move', 'search', [[('name', '=', payment_name)]], {'limit': 1})
             if move_search:
                 move_id = move_search[0]
             else:
                 move_search = client.execute_kw('account.move', 'search', [[('ref', '=', payment_name)]], {'limit': 1})
                 if move_search:
                     move_id = move_search[0]

        if not move_id:
            _logger.warning(f"  Could not find move_id for Payment {payment_id}. Skipping reconciliation.")
            return

        # Search lines of this move (Payment)
        # Outbound payment has Dr on Payable.
        lines = client.execute_kw('account.move.line', 'search_read', 
            [[('move_id', '=', move_id), ('account_id.account_type', '=', 'liability_payable')]],
            {'fields': ['id', 'credit', 'debit']}
        )
        
        if not lines:
            return

        payment_line_id = lines[0]['id']
        payment_amount = lines[0]['debit'] # Outbound payment (Debit on Payable)

        matched_line_id = False

        # METHOD 1: Match by Memo (Bill Name)
        memo = payment[0].get('memo')
        if memo:
            _logger.info(f"  Attempting match by Memo: {memo}")
            # Search for Vendor Bill with this name/ref
            # Usually Vendor Bill 'name' is auto-generated (BILL/...), 'ref' is the Vendor's invoice number.
            # Odoo 14 'Ref' might be mapped to 'ref' in Odoo 19 Bill?
            # Let's search 'ref' and 'name'.
            inv_search = client.execute_kw('account.move', 'search_read', 
                [[('name', '=', memo), ('move_type', '=', 'in_invoice'), ('state', '=', 'posted'), ('payment_state', '!=', 'paid')]], 
                {'fields': ['id', 'name'], 'limit': 1}
            )
            if not inv_search:
                 inv_search = client.execute_kw('account.move', 'search_read', 
                    [[('ref', '=', memo), ('move_type', '=', 'in_invoice'), ('state', '=', 'posted'), ('payment_state', '!=', 'paid')]], 
                    {'fields': ['id', 'name'], 'limit': 1}
                )
            
            if inv_search:
                inv_id = inv_search[0]['id']
                # Get Payable Line of Invoice (Credit side)
                inv_lines = client.execute_kw('account.move.line', 'search_read', 
                    [[('move_id', '=', inv_id), ('account_id.account_type', '=', 'liability_payable'), ('reconciled', '=', False)]],
                    {'fields': ['id', 'credit']}
                )
                if inv_lines:
                    matched_line_id = inv_lines[0]['id']
                    _logger.info(f"  Found Vendor Bill {memo} via Memo match.")

        # METHOD 2: Fallback to Amount Match
        if not matched_line_id:
            _logger.info("  Fallback to Amount Match...")
            # Find Open Bills for Partner
            invoice_domain = [
                ('parent_state', '=', 'posted'),
                ('account_id.account_type', '=', 'liability_payable'),
                ('partner_id', '=', partner_id),
                ('reconciled', '=', False),
                ('move_id.move_type', '=', 'in_invoice'),
                ('credit', '>', 0)
            ]
            
            open_lines = client.execute_kw('account.move.line', 'search_read', 
                [invoice_domain], 
                {'fields': ['id', 'move_name', 'credit', 'date_maturity']}
            )
            
            if open_lines:
                for line in open_lines:
                    if abs(line['credit'] - payment_amount) < 0.01:
                        matched_line_id = line['id']
                        _logger.info(f"  Found Exact Amount Match: {line['move_name']}")
                        break
        
        if matched_line_id:
             client.execute_kw('account.move.line', 'reconcile', [[payment_line_id, matched_line_id]])
             _logger.info("  Reconciled successfully")
        else:
             _logger.warning("  No matching bill found to reconcile.")

    except Exception as e:
        _logger.error(f"Reconciliation check failed: {e}")

def main():
    parser = argparse.ArgumentParser(description='Migrate Vendor Payments')
    # Odoo 14
    parser.add_argument('--src-url', default='https://erpmfs.com', help='Source Odoo 14 URL')
    parser.add_argument('--src-db', default='metro_production_8_8_22', help='Source Odoo 14 DB')
    parser.add_argument('--src-user', default='Sales.auh@metrofiresystems.com', help='Source Odoo 14 User')
    parser.add_argument('--src-password', default='Sales@185734', help='Source Odoo 14 Password')

    # Odoo 19
    parser.add_argument('--dest-url', default='http://localhost:8079', help='Dest Odoo 19 URL')
    parser.add_argument('--dest-db', default='metrodb', help='Dest Odoo 19 User')
    parser.add_argument('--dest-user', default='admin', help='Dest Odoo 19 User')
    parser.add_argument('--dest-password', default='Amaze@321', help='Dest Odoo 19 Password')
    
    parser.add_argument('--limit', type=int, default=200, help='Limit number of records')

    args = parser.parse_args()

    # 1. Connect
    src_client = OdooJsonRpcClient(args.src_url, args.src_db, args.src_user, args.src_password)
    dest_client = OdooJsonRpcClient(args.dest_url, args.dest_db, args.dest_user, args.dest_password)
    
    if not src_client.authenticate():
        print(f"Failed to authenticate with Source {args.src_url}")
        return
    if not dest_client.authenticate():
        print(f"Failed to authenticate with Destination {args.dest_url}")
        return
        
    print("Connected to Source and Destination.")

    # 2. Fetch Odoo 14 Payments (Loop for Batches)
    offset = 0
    total_migrated = 0
    
    while True:
        print(f"\n--- Starting Batch (Offset: {offset}, Limit: {args.limit}) ---")
        try:
            domain = [
                ('payment_type', '=', 'outbound'),
                ('partner_type', '=', 'supplier'),
                ('state', '=', 'posted')
            ]
            fields_to_fetch = ['name', 'date', 'amount', 'ref', 'partner_id', 'journal_id', 'branch_id']
            
            # Fetch Source Payments
            payments = src_client.execute_kw('account.payment', 'search_read', [domain], 
                {'fields': fields_to_fetch, 'limit': args.limit, 'offset': offset, 'order': 'date desc'})
            
            if not payments:
                print("No more payments found in source.")
                break
                
        except Exception as e:
            print(f"Failed to fetch payments: {e}")
            break
    
        print(f"Fetched {len(payments)} payments.")
        batch_processed_count = 0

        # 3. Migrate Batch
        for pay in payments:
            batch_processed_count += 1
            # Check if this payment already exists in Destination (by Name)
            existing_pay = dest_client.execute_kw('account.payment', 'search_count', [[('name', '=', pay['name'])]])
            if existing_pay > 0:
                 print(f"Skipping {pay['name']} - Already Exists")
                 continue

            try:
                print(f"Processing Payment: {pay.get('name')}")
                
                # Map Partner
                src_partner_name = pay['partner_id'][1] if pay['partner_id'] else False
                dest_partner_id = False
                if src_partner_name:
                    partner_search = dest_client.execute_kw('res.partner', 'search', [[('name', '=', src_partner_name)]], {'limit': 1})
                    if partner_search:
                        dest_partner_id = partner_search[0]
                
                if not dest_partner_id:
                    print(f"  Skipping: Partner '{src_partner_name}' not found.")
                    continue

                # Map Company
                branch_name = pay.get('branch_id', [0, ''])[1] if pay.get('branch_id') else ''
                dest_company_id = get_dest_company_id(dest_client, branch_name)

                # Map Journal
                src_journal_name = pay['journal_id'][1] if pay['journal_id'] else ''
                dest_journal_id = False
                if src_journal_name:
                    journal_search = dest_client.execute_kw('account.journal', 'search', 
                        [[('name', '=', src_journal_name), ('company_id', '=', dest_company_id)]], {'limit': 1})
                    if not journal_search:
                         journal_search = dest_client.execute_kw('account.journal', 'search', 
                            [[('type', 'in', ['bank', 'cash']), ('company_id', '=', dest_company_id)]], {'limit': 1})
                    if journal_search:
                        dest_journal_id = journal_search[0]

                if not dest_journal_id:
                     print(f"  Skipping: Journal '{src_journal_name}' not found.")
                     continue

                # Register Payment needs currency
                currency_data = dest_client.execute_kw('res.company', 'read', [[dest_company_id], ['currency_id']])
                currency_id = currency_data[0]['currency_id'][0] if currency_data else False
                
                # ---------------------------------------------------------
                # STRATEGY: Try to Pay Bill directly (Register Payment)
                # ---------------------------------------------------------
                invoice_found = False
                memo = pay.get('ref') or pay['name']
                
                # Search for Vendor Bill
                if memo:
                    inv_search = dest_client.execute_kw('account.move', 'search_read', 
                        [[('name', '=', memo), ('move_type', '=', 'in_invoice'), ('state', '=', 'posted'), ('payment_state', '!=', 'paid')]], 
                        {'fields': ['id', 'name', 'amount_residual'], 'limit': 1}
                    )
                    # Try REF too
                    if not inv_search:
                        inv_search = dest_client.execute_kw('account.move', 'search_read', 
                            [[('ref', '=', memo), ('move_type', '=', 'in_invoice'), ('state', '=', 'posted'), ('payment_state', '!=', 'paid')]], 
                            {'fields': ['id', 'name', 'amount_residual'], 'limit': 1}
                        )

                    if inv_search:
                         invoice_id = inv_search[0]['id']
                         invoice_name = inv_search[0]['name']
                         invoice_found = True
                         print(f"  Found Bill {invoice_name} (ID: {invoice_id}). Using Register Payment.")
                         
                         ctx = {
                             'active_model': 'account.move',
                             'active_ids': [invoice_id],
                         }
                         
                         wiz_vals = {
                             'journal_id': dest_journal_id,
                             'amount': pay['amount'],
                             'payment_date': pay['date'],
                             'communication': memo,
                             'currency_id': currency_id,
                             'payment_method_line_id': False, 
                         }
                         
                         # Check for manual method
                         pml_search = dest_client.execute_kw('account.payment.method.line', 'search',
                             [[('journal_id', '=', dest_journal_id), ('code', '=', 'manual'), ('payment_type', '=', 'outbound')]], {'limit': 1}
                         )
                         if pml_search:
                             wiz_vals['payment_method_line_id'] = pml_search[0]
                         
                         wiz_id = dest_client.execute_kw('account.payment.register', 'create', [wiz_vals], {'context': ctx})
                         
                         res_action = dest_client.execute_kw('account.payment.register', 'action_create_payments', [[wiz_id]], {'context': ctx})
                         print("  Payment Registered via Wizard.")
                         
                         # Search and Rename
                         new_pay_search = dest_client.execute_kw('account.payment', 'search_read',
                            [[('amount', '=', pay['amount']), ('memo', '=', memo), ('journal_id', '=', dest_journal_id)]],
                            {'fields': ['id', 'name'], 'order': 'id desc', 'limit': 1}
                         )
                         
                         if new_pay_search:
                             new_payment_id = new_pay_search[0]['id']
                             current_name = new_pay_search[0]['name']
                             target_name = pay['name']
                             
                             if current_name != target_name:
                                 print(f"  Renaming {current_name} -> {target_name}")
                                 dest_client.execute_kw('account.payment', 'write', [[new_payment_id], {'name': target_name}])
                                 
                             # Validate
                             try:
                                 print(f"  Validating...")
                                 dest_client.execute_kw('account.payment', 'action_validate', [[new_payment_id]])
                                 
                                 # Mark as Paid
                                 mark_payment_as_cleared(dest_client, new_payment_id)
                                 
                             except Exception as e:
                                 print(f"  Validation failed: {e}")
    
                
                # ---------------------------------------------------------
                # FALLBACK: Create Detached Payment
                # ---------------------------------------------------------
                if not invoice_found:
                    print("  Bill not found. Creating detached payment.")
                    vals = {
                        'payment_type': 'outbound',
                        'partner_type': 'supplier',
                        'partner_id': dest_partner_id,
                        'amount': pay['amount'],
                        'date': pay['date'],
                        'name': pay['name'],
                        'memo': memo,
                        'journal_id': dest_journal_id,
                        'company_id': dest_company_id,
                        'currency_id': currency_id,
                    }
                    
                    new_payment_id = dest_client.execute_kw('account.payment', 'create', [vals])
                    print(f"  Created Payment ID: {new_payment_id}")
                    
                    dest_client.execute_kw('account.payment', 'write', [[new_payment_id], {'name': pay['name']}])
                    dest_client.execute_kw('account.payment', 'action_post', [[new_payment_id]])

                    reconcile_payment(dest_client, new_payment_id, dest_partner_id)
    
            except Exception as e:
                print(f"  Error processing payment {pay.get('name')}: {e}")
        
        offset += args.limit
        total_migrated += batch_processed_count
        print(f"--- Batch Completed. Total processed so far: {total_migrated}. Offset now: {offset} ---\n")
        time.sleep(1)

if __name__ == "__main__":
    main()
