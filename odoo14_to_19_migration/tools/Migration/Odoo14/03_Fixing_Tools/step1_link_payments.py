import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

# 1st Step: Link payments with customer invoice, using memo

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

c_id = models.execute_kw(db, uid, password, 'res.company', 'search', [[('name', '=', 'ABU DHABI')]])[0]

# Find ALL unlinked payments (where is_reconciled is False)
payments = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [
    [('company_id', '=', c_id), ('is_reconciled', '=', False), ('memo', '!=', False)]
], {'fields': ['id', 'name', 'memo', 'move_id']})

print(f"Found {len(payments)} unlinked payments with a memo.")

linked_count = 0
for p in payments:
    memo = p.get('memo')
    pay_move_id = p['move_id'][0] if p.get('move_id') else False
    
    if not pay_move_id or not memo:
        continue
        
    # Get the receivable line of the payment itself
    pay_lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read', [
        [('move_id', '=', pay_move_id), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]
    ], {'fields': ['id']})
    
    if not pay_lines:
        continue
        
    payment_line_id = pay_lines[0]['id']
    
    # Search for the Invoice matching the Memo exactly
    invs = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
        [('name', '=', memo), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('company_id', '=', c_id), ('payment_state', '!=', 'paid')]
    ], {'fields': ['id']})
    
    if invs:
        inv_id = invs[0]['id']
        # Get the receivable line of the invoice
        inv_lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read', [
            [('move_id', '=', inv_id), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]
        ], {'fields': ['id']})
        
        if inv_lines:
            invoice_line_id = inv_lines[0]['id']
            # Step 1: Link payment line with invoice line
            try:
                models.execute_kw(db, uid, password, 'account.move.line', 'reconcile', [[payment_line_id, invoice_line_id]])
                print(f"Linked Payment {p['name']} with Invoice {memo}")
                linked_count += 1
            except Exception as e:
                if "marshal None" in str(e):
                    print(f"Linked Payment {p['name']} with Invoice {memo}")
                    linked_count += 1
                else:
                    print(f"Error linking {p['name']} -> {memo}: {e}")

print(f"\nStep 1 Complete. Linked {linked_count} payments to invoices.")
