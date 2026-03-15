import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

c_ids = models.execute_kw(db, uid, password, 'res.company', 'search', [[]])

print(f"Authenticated as uid {uid}. Connected to companies: {c_ids}")

# Get all inbound payments that are not reconciled and have a memo
domain = [
    ('is_reconciled', '=', False),
    ('memo', '!=', False),
    ('state', 'in', ['in_process', 'posted'])
]

pays = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [domain], {
    'fields': ['id', 'name', 'memo', 'move_id', 'company_id', 'state', 'partner_id', 'amount']
})

print(f"Found {len(pays)} unlinked inbound payments with a memo.")

linked_count = 0
failed_count = 0

for p in pays:
    memo = p['memo']
    if not memo:
        continue
        
    payment_id = p['id']
    pay_move_id = p['move_id'][0] if p.get('move_id') else False
    c_id = p['company_id'][0]
    
    if not pay_move_id:
        print(f"Payment {p['name']} has no move_id. Skipping.")
        failed_count += 1
        continue
        
    # Get the receivable line of the payment
    pay_lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read', [
        [('move_id', '=', pay_move_id), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]
    ], {'fields': ['id']})
    
    if not pay_lines:
        print(f"Payment {p['name']} has no unreconciled receivable line. Skipping.")
        failed_count += 1
        continue
        
    payment_line_id = pay_lines[0]['id']
    
    # Try to find the invoice based on the memo
    partner_id = p['partner_id'][0] if p.get('partner_id') else False
    
    inv_domain = [
        ('move_type', '=', 'out_invoice'), 
        ('state', '=', 'posted'), 
        ('payment_state', 'in', ['not_paid', 'partial']), 
        ('company_id', '=', c_id),
        '|', ('name', '=', memo), ('name', 'ilike', '%' + memo + '%')
    ]
    
    if partner_id:
        inv_domain.insert(0, ('partner_id', '=', partner_id))
        
    invs = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
        inv_domain
    ], {'fields': ['id', 'name', 'payment_state']})
    
    if not invs:
        # If not found with partner, we can try without partner just in case, but it's safer to skip
        print(f"Payment {p['name']} memo '{memo}' (Amount: {p['amount']}) -> No matching unpaid invoice found. Skipping.")
        failed_count += 1
        continue
        
    # If multiple invoices match, prioritize exact match on name
    exact_match = [i for i in invs if i['name'] == memo]
    target_inv = exact_match[0] if exact_match else invs[0]
    inv_id = target_inv['id']
    
    print(f"Linking Payment {p['name']} (Memo: {memo}) line {payment_line_id} to Invoice {target_inv['name']} (ID {inv_id})...")
    
    try:
        res = models.execute_kw(db, uid, password, 'account.move', 'js_assign_outstanding_line', [[inv_id], payment_line_id])
        print(f"  -> Linked successfully")
        linked_count += 1
    except Exception as e:
        print(f"  -> Error linking: {e}")
        failed_count += 1

print(f"\nSummary:")
print(f"Total processed: {len(pays)}")
print(f"Successfully linked: {linked_count}")
print(f"Failed to link: {failed_count}")
