import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

# Get ABU DHABI company
comp = models.execute_kw(db, uid, password, 'res.company', 'search', [[('name', '=', 'ABU DHABI')]])
if not comp:
    print("Company not found")
    exit()
c_id = comp[0]

print(f"Scanning payments for company ID {c_id}...")

# Find a paid payment with a memo in ABU DHABI
payments = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [
    [('company_id', '=', c_id), ('state', 'in', ['paid', 'in_process']), ('memo', '!=', False)]
], {'fields': ['name', 'memo', 'move_id', 'partner_id']})

print(f"Total payments to process: {len(payments)}")
success_count = 0
not_found_count = 0

for p in payments:
    pay_name = p['name']
    memo = p.get('memo')
    partner_id = p.get('partner_id')[0] if p.get('partner_id') else False
    move_id = p.get('move_id')[0] if p.get('move_id') else None
    if not move_id or not memo:
        continue
        
    # Get receivable lines of payment
    pay_lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read', [
        [('move_id', '=', move_id), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]
    ], {'fields': ['id', 'credit']})
    
    if not pay_lines:
        continue # Already Reconciled
        
    payment_line_id = pay_lines[0]['id']
    payment_amount = pay_lines[0]['credit']
    
    matched_line_id = False
    
    # 1. Look for invoice by memo
    invs = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
        [('name', '=', memo), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('payment_state', '!=', 'paid'), ('company_id', '=', c_id)]
    ], {'fields': ['id', 'name', 'payment_state']})
    
    if invs:
        inv_id = invs[0]['id']
        inv_lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read', [
            [('move_id', '=', inv_id), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]
        ], {'fields': ['id', 'debit']})
        
        if inv_lines:
            matched_line_id = inv_lines[0]['id']
            
    # 2. Match by exact amount and partner if memo string match failed
    if not matched_line_id and partner_id:
        invoice_domain = [
            ('parent_state', '=', 'posted'),
            ('account_id.account_type', '=', 'asset_receivable'),
            ('partner_id', '=', partner_id),
            ('reconciled', '=', False),
            ('move_id.move_type', '=', 'out_invoice'),
            ('company_id', '=', c_id),
            ('debit', '>', 0)
        ]
        open_lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read', [invoice_domain], {'fields': ['id', 'move_name', 'debit']})
        
        if open_lines:
            for line in open_lines:
                if abs(line['debit'] - payment_amount) < 0.01:
                    matched_line_id = line['id']
                    break
                    
    # Reconcile if a matching open line is found
    if matched_line_id:
        try:
             models.execute_kw(db, uid, password, 'account.move.line', 'reconcile', [[payment_line_id, matched_line_id]])
             print(f"Reconciled Invoice '{memo}' with Payment '{pay_name}'.")
             success_count += 1
        except Exception as e:
             # Ignores TypeError: cannot marshal None
             if "marshal None" in str(e):
                 print(f"Reconciled Invoice '{memo}' with Payment '{pay_name}'.")
                 success_count += 1
             else:
                 print(f"Error Reconciling '{pay_name}': {e}")
    else:
        not_found_count += 1
        
print(f"Finished. Reconciled: {success_count}. Missing/Unmatched: {not_found_count}.")
