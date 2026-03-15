import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

comp = models.execute_kw(db, uid, password, 'res.company', 'search', [[('name', '=', 'ABU DHABI')]])
if not comp:
    print("Company not found")
    exit()
c_id = comp[0]

print(f"Scanning payments for company ID {c_id} to mark as cleared...")

payments = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [
    [('company_id', '=', c_id), ('state', '=', 'in_process')]
], {'fields': ['id', 'name', 'move_id', 'journal_id', 'date', 'amount', 'currency_id']})

print(f"Found {len(payments)} payments in 'in_process' state.")

success_count = 0
failed_count = 0

for p in payments:
    try:
        payment_id = p['id']
        move_id = p['move_id'][0] if p.get('move_id') else False
        journal_id = p['journal_id'][0] if p.get('journal_id') else False
        payment_date = p['date']
        amount = p['amount']
        currency_id = p['currency_id'][0] if p.get('currency_id') else False
        payment_name = p['name']

        if not move_id or not journal_id:
            continue

        lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read', 
            [[('move_id', '=', move_id), ('reconciled', '=', False), ('account_id.account_type', '!=', 'asset_receivable'), ('account_id.account_type', '!=', 'liability_payable')]],
            {'fields': ['id', 'account_id', 'debit', 'credit', 'name']}
        )
        
        if not lines:
            continue

        liquidity_line = lines[0]
        outstanding_account_id = liquidity_line['account_id'][0]
        
        journal_data = models.execute_kw(db, uid, password, 'account.journal', 'read', [[journal_id], ['default_account_id']])
        if not journal_data or not journal_data[0]['default_account_id']:
            continue

        bank_account_id = journal_data[0]['default_account_id'][0]
        
        if bank_account_id == outstanding_account_id:
            continue

        clearance_move_vals = {
            'journal_id': journal_id,
            'date': payment_date,
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {
                    'account_id': bank_account_id,
                    'name': f"Bank Clearance - {payment_name}",
                    'debit': amount,
                    'credit': 0.0,
                    'currency_id': currency_id,
                }),
                (0, 0, {
                    'account_id': outstanding_account_id,
                    'name': f"Clearance - {payment_name}",
                    'debit': 0.0,
                    'credit': amount,
                    'currency_id': currency_id,
                })
            ]
        }
        
        clearance_move_id = models.execute_kw(db, uid, password, 'account.move', 'create', [clearance_move_vals])
        models.execute_kw(db, uid, password, 'account.move', 'action_post', [[clearance_move_id]])
        
        clearance_lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read', 
            [[('move_id', '=', clearance_move_id), ('account_id', '=', outstanding_account_id)]],
            {'fields': ['id']}
        )
        
        if clearance_lines:
            try:
                models.execute_kw(db, uid, password, 'account.move.line', 'reconcile', [[liquidity_line['id'], clearance_lines[0]['id']]])
                success_count += 1
                print(f"Payment '{payment_name}' marked as fully PAID.")
            except Exception as e:
                # Ignores TypeError: cannot marshal None
                if "marshal None" in str(e):
                    success_count += 1
                    print(f"Payment '{payment_name}' marked as fully PAID.")
                else:
                    failed_count += 1
                    print(f"Error Reconciling '{payment_name}': {e}")
    except Exception as e:
        failed_count += 1
        print(f"Failed to clear {payment_name}: {e}")

print(f"Finished. Cleared: {success_count}. Failed: {failed_count}.")
