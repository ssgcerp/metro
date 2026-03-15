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

# Specific domain for dry run test
domain = [
    ('name', '=', 'PBNK1/2023/00185'),
    ('is_reconciled', '=', False),
    ('memo', '!=', False)
]

pays = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [domain], {
    'fields': ['id', 'name', 'memo', 'move_id', 'company_id', 'state', 'partner_id', 'amount', 'date', 'journal_id']
})

print(f"Found {len(pays)} payments matching 'PBNK1/2023/00185'.")

for p in pays:
    raw_memo = p['memo']
    if not raw_memo:
        continue
        
    payment_id = p['id']
    amount = p['amount']
    date = p['date']
    partner_id = p['partner_id'][0] if p.get('partner_id') else False
    journal_id = p['journal_id'][0] if p.get('journal_id') else False
    
    print(f"\nProcessing Payment: {p['name']} | Amount: {amount} | Memo: '{raw_memo}'")
    
    # Split memo by comma in case there are multiple invoice numbers
    memo_parts = [m.strip() for m in str(raw_memo).split(',')]
    
    for memo in memo_parts:
        if not memo:
            continue
            
        print(f"  -> Looking for Invoice matching memo part: '{memo}'")
        
        # Domain: Invoice must be posted, unpaid/partial, and either name exact match OR name ends with memo
        # Frequently odoo sequences are like INV/2023/10360, so we check if name ilike '%10360'
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
        
        if not invs:
            print(f"    [!] No matching unpaid invoice found for '{memo}'.")
            continue
            
        # Get the first matching invoice
        target_inv = invs[0]
        inv_id = target_inv['id']
        inv_name = target_inv['name']
        residual = target_inv['amount_residual']
        
        print(f"    [+] Found Invoice: {inv_name} (ID: {inv_id}) | Amount Due: {residual}")
        print(f"    [DRY RUN] Would link Payment {p['name']} to Invoice {inv_name}")
