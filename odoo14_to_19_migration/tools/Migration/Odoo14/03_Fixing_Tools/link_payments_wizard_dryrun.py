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
    'fields': ['id', 'name', 'memo', 'move_id', 'company_id', 'state', 'partner_id', 'amount', 'date', 'journal_id'],
    'limit': 50
})

print(f"Found {len(pays)} unlinked inbound payments with a memo (Dry Run execution limited).")

linked_count = 0
failed_count = 0

for p in pays:
    memo = p['memo']
    if not memo:
        continue
        
    payment_id = p['id']
    c_id = p['company_id'][0]
    amount = p['amount']
    date = p['date']
    partner_id = p['partner_id'][0] if p.get('partner_id') else False
    journal_id = p['journal_id'][0] if p.get('journal_id') else False
    
    # Try to find the invoice based on the memo - do not filter by company_id because payments and invoices might be in different companies due to import quirks
    inv_domain = [
        ('move_type', '=', 'out_invoice'), 
        ('state', '=', 'posted'), 
        ('payment_state', 'in', ['not_paid', 'partial']), 
        '|', ('name', '=', memo), ('name', 'ilike', '%' + memo + '%')
    ]
    
    if partner_id:
        inv_domain.insert(0, ('partner_id', '=', partner_id))
        
    invs = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
        inv_domain
    ], {'fields': ['id', 'name', 'payment_state', 'company_id']})
    
    if not invs:
        print(f"[DRY RUN] Payment {p['name']} memo '{memo}' (Amount: {amount}) -> No matching unpaid invoice found. Would skip.")
        failed_count += 1
        continue
        
    # If multiple invoices match, prioritize exact match on name
    exact_match = [i for i in invs if i['name'] == memo]
    target_inv = exact_match[0] if exact_match else invs[0]
    inv_id = target_inv['id']
    
    print(f"[DRY RUN] Would recreate Payment {p['name']} (Memo: {memo}) to link with Invoice {target_inv['name']} (ID {inv_id})...")
    
    # In dry run mode, we don't actually do anything
    # We just log it
    print(f"  -> [DRY RUN] Would delete payment {payment_id} and register new payment for invoice {inv_id}")
    linked_count += 1

print(f"\nDry Run Summary:")
print(f"Total processed: {len(pays)}")
print(f"Would attempt to recreate and link: {linked_count}")
print(f"Would fail to link: {failed_count}")
