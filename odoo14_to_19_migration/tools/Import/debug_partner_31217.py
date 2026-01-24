
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    pid = 31217
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
    
    lines = models.execute_kw(DB, uid, PASS, 'account.move.line', 'search_read', [[('partner_id', '=', pid), ('account_type', '=', 'liability_payable'), ('reconciled', '=', False)]], {'fields': ['id', 'company_id', 'account_id', 'amount_residual', 'move_id']})
    
    print(f"Lines for Partner {pid}:")
    for l in lines:
        print(f"ID {l['id']} | Comp {l['company_id']} | Acc {l['account_id']} | Residual {l['amount_residual']}")
        # Check details of move
        mid = l['move_id'][0]
        move = models.execute_kw(DB, uid, PASS, 'account.move', 'read', [[mid], ['company_id', 'journal_id']])[0]
        print(f"  Move {mid} | Comp {move['company_id']} | Journal {move['journal_id']}")

if __name__ == "__main__":
    main()
