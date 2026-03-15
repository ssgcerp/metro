import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context(), allow_none=True)
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context(), allow_none=True)

c_ids = models.execute_kw(db, uid, password, 'res.company', 'search', [[]])
print(f"Authenticated as uid {uid}. Connected to companies: {c_ids}")

# Get all inbound payments that are not reconciled and have a memo
domain = [
    ('is_reconciled', '=', False),
    ('memo', '!=', False),
    ('state', 'in', ['in_process', 'posted'])
]

pays = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [domain], {
    'fields': ['id', 'name', 'memo', 'move_id', 'company_id', 'state', 'partner_id', 'amount', 'date', 'journal_id']
})

print(f"Found {len(pays)} unlinked inbound payments with a memo.")

linked_count = 0
failed_count = 0

for p in pays:
    raw_memo = p['memo']
    if not raw_memo:
        continue
        
    payment_id = p['id']
    amount = p['amount']
    date = p['date']
    partner_id = p['partner_id'][0] if p.get('partner_id') else False
    journal_id = p['journal_id'][0] if p.get('journal_id') else False
    
    # Extract multiple invoice numbers separated by commas
    memo_parts = [m.strip() for m in str(raw_memo).split(',')]
    valid_memos = [m for m in memo_parts if m]
    
    if not valid_memos:
        continue
        
    print(f"\nProcessing Payment: {p['name']} | Amount: {amount} | Memo: '{raw_memo}'")
    
    # Try to find all matching invoices first
    matched_invoices = []
    total_due = 0.0
    
    for memo in valid_memos:
        inv_domain = [
            ('move_type', '=', 'out_invoice'), 
            ('state', '=', 'posted'), 
            ('payment_state', 'in', ['not_paid', 'partial']), 
            '|', ('name', '=', memo), ('name', '=ilike', '%' + memo)
        ]
        
        if partner_id:
            inv_domain.insert(0, ('partner_id', '=', partner_id))
            
        invs = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
            inv_domain
        ], {'fields': ['id', 'name', 'payment_state', 'amount_residual']})
        
        if invs:
            # We take the first match for this memo part
            matched_inv = invs[0]
            matched_invoices.append(matched_inv)
            total_due += matched_inv['amount_residual']
        else:
            print(f"  [!] No matching unpaid invoice found for memo part: '{memo}'")
            
    if not matched_invoices:
        print(f"  -> Could not find any invoices for memo '{raw_memo}'. Skipping.")
        failed_count += 1
        continue
        
    # We found at least one invoice. Now we delete the old payment.
    try:
        try: models.execute_kw(db, uid, password, 'account.payment', 'action_draft', [[payment_id]])
        except: pass
        try: models.execute_kw(db, uid, password, 'account.payment', 'action_cancel', [[payment_id]])
        except: pass
        try: models.execute_kw(db, uid, password, 'account.payment', 'unlink', [[payment_id]])
        except: pass
        
        remaining_payment_amount = amount
        
        # Now create payments for each matched invoice
        for i, target_inv in enumerate(matched_invoices):
            inv_id = target_inv['id']
            residual = target_inv['amount_residual']
            
            # If this is the last invoice, allocate all remaining payment amount to it
            # Otherwise, pay up to the invoice's residual amount
            if i == len(matched_invoices) - 1:
                payment_amount_for_inv = remaining_payment_amount
            else:
                payment_amount_for_inv = min(residual, remaining_payment_amount)
                
            if payment_amount_for_inv <= 0:
                print(f"  -> No remaining payment amount for invoice {target_inv['name']}. Skipping.")
                continue
                
            print(f"  -> Recreating Payment (Portion: {payment_amount_for_inv}) to link with Invoice {target_inv['name']} (ID {inv_id})...")
            
            # CREATE payment safely linked to invoice via wizard
            wiz_vals = {
                'journal_id': journal_id,
                'payment_date': date,
                'amount': payment_amount_for_inv,
                'communication': valid_memos[i], # Assign the specific memo part
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': partner_id
            }
            
            ctx = {'active_model': 'account.move', 'active_ids': [inv_id], 'active_id': inv_id}
            wiz_id = models.execute_kw(db, uid, password, 'account.payment.register', 'create', [wiz_vals], {'context': ctx})
            
            # This will create the payment and reconcile it with the invoice
            new_pay = models.execute_kw(db, uid, password, 'account.payment.register', 'action_create_payments', [[wiz_id]], {'context': ctx})
            
            # Force payment state to paid if needed
            if new_pay and isinstance(new_pay, dict) and 'res_id' in new_pay:
                new_pay_id = new_pay['res_id']
                try:
                    models.execute_kw(db, uid, password, 'account.payment', 'write', [[new_pay_id], {'state': 'paid'}])
                except Exception as e:
                    if "cannot marshal None unless allow_none is enabled" not in str(e):
                        print(f"    -> Warning forcing paid: {e}")
                        
            remaining_payment_amount -= payment_amount_for_inv
            linked_count += 1
            print(f"    -> Successfully linked portion to {target_inv['name']}")
            
    except Exception as e:
        print(f"  -> Error recreating/linking: {e}")
        failed_count += 1

print(f"\nSummary:")
print(f"Total processed payments: {len(pays)}")
print(f"Successfully recreated and linked (portions): {linked_count}")
print(f"Failed completely: {failed_count}")
