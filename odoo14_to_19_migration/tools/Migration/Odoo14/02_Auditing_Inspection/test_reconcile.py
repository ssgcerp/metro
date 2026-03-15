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

# Find a paid payment with a memo in ABU DHABI
payments = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [
    [('company_id', '=', c_id), ('state', 'in', ['paid', 'in_process']), ('memo', '!=', False)]
], {'fields': ['name', 'memo', 'move_id', 'partner_id'], 'limit': 5})

for p in payments:
    print(f"Payment {p['name']}, Memo: {p.get('memo')}, Partner: {p.get('partner_id')}")
    memo = p.get('memo')
    move_id = p.get('move_id')[0] if p.get('move_id') else None
    if not move_id:
        continue
        
    print(f"Move ID: {move_id}")
    
    # 1. Look for invoice by memo
    invs = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
        [('name', '=', memo), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]
    ], {'fields': ['id', 'name', 'payment_state']})
    
    if invs:
        print(f"Found Invoice matching memo: {invs[0]['name']}, payment_state: {invs[0]['payment_state']}")
        inv_id = invs[0]['id']
        
        # Get receivable lines of invoice
        inv_lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read', [
            [('move_id', '=', inv_id), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]
        ], {'fields': ['id', 'debit', 'credit']})
        
        # Get receivable lines of payment
        pay_lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read', [
            [('move_id', '=', move_id), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]
        ], {'fields': ['id', 'debit', 'credit']})
        
        print(f"Invoice Receivables: {inv_lines}")
        print(f"Payment Receivables: {pay_lines}")
        
    print("-" * 40)
