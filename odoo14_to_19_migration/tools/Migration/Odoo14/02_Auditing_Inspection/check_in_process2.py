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
c_id = comp[0]

payments = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [
    [('company_id', '=', c_id), ('state', '=', 'in_process')]
], {'fields': ['id', 'name', 'move_id', 'journal_id', 'state', 'is_reconciled', 'outstanding_account_id'], 'limit': 2})

for p in payments:
    print(f"Payment {p['name']}")
    move_id = p['move_id'][0] if p.get('move_id') else False
    if not move_id: 
        print("  No move!")
        continue
    
    lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read', 
        [[('move_id', '=', move_id)]],
        {'fields': ['id', 'account_id', 'debit', 'credit', 'name', 'reconciled']}
    )
    for l in lines:
        print(f"  Line {l['id']}: account={l['account_id'][1]} | reconciled={l['reconciled']}")

    journal_id = p['journal_id'][0] if p.get('journal_id') else False
    journal_data = models.execute_kw(db, uid, password, 'account.journal', 'read', [[journal_id], ['default_account_id']])
    print(f"  Journal default account: {journal_data[0]['default_account_id'] if journal_data[0].get('default_account_id') else 'None'}")
