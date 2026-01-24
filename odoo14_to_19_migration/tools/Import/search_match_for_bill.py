
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print("SEARCHING MATCH FOR BILL SI-550100035722")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    # Bill Details
    bill_id = 53792
    bill = models.execute_kw(DB, uid, PASS, 'account.move', 'read', [[bill_id], ['name', 'amount_total', 'amount_residual', 'ref', 'partner_id']])[0]
    print(f"Bill: {bill['name']} | Ref: {bill['ref']} | Total: {bill['amount_total']} | Residual: {bill['amount_residual']}")
    
    # 1. Search by exact amount
    print(f"\nSearching payments with amount {bill['amount_total']}...")
    p_ids = models.execute_kw(DB, uid, PASS, 'account.payment', 'search', [[('amount', '=', bill['amount_total']), ('partner_type', '=', 'supplier'), ('state', 'in', ['posted', 'paid'])]])
    if p_ids:
        res = models.execute_kw(DB, uid, PASS, 'account.payment', 'read', [p_ids, ['name', 'amount', 'memo', 'state']])
        for r in res:
            print(f"  Match by Amount: {r}")

    # 2. Search by memo
    print(f"\nSearching payments with memo like '{bill['name']}' or '{bill['ref']}'...")
    domain = [('memo', 'ilike', bill['name'])]
    if bill['ref']:
        domain = ['|'] + domain + [('memo', 'ilike', bill['ref'])]
        
    p_ids = models.execute_kw(DB, uid, PASS, 'account.payment', 'search', [[('partner_type', '=', 'supplier')] + domain])
    if p_ids:
        res = models.execute_kw(DB, uid, PASS, 'account.payment', 'read', [p_ids, ['name', 'amount', 'memo', 'state']])
        for r in res:
            print(f"  Match by Text: {r}")
            
    # 3. Search unreconciled moves
    print("\nSearching for any unreconciled payment move lines for this partner...")
    partner_id = bill['partner_id'][0]
    l_ids = models.execute_kw(DB, uid, PASS, 'account.move.line', 'search', [[('partner_id', '=', partner_id), ('account_id.account_type', '=', 'liability_payable'), ('full_reconcile_id', '=', False)]])
    if l_ids:
        res = models.execute_kw(DB, uid, PASS, 'account.move.line', 'read', [l_ids, ['move_id', 'name', 'debit', 'credit', 'amount_residual']])
        for r in res:
             print(f"  Partner Unreconciled Line {r['id']}: Move {r['move_id'][1]} | Dr {r['debit']} | Cr {r['credit']} | Name {r['name']}")

if __name__ == "__main__":
    main()
