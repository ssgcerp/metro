
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
    
    lines = models.execute_kw(DB, uid, PASS, 'account.move.line', 'search_read', [[('account_type', '=', 'liability_payable'), ('reconciled', '=', False)]], {'fields': ['id', 'partner_id', 'company_id', 'amount_residual']})
    
    pg = {}
    for l in lines:
        if not l['partner_id']: continue
        pid = l['partner_id'][0]
        pname = l['partner_id'][1]
        cid = l['company_id'][0]
        if pid not in pg: pg[pid] = {'name': pname, 'branches': {}}
        pg[pid]['branches'][cid] = pg[pid]['branches'].get(cid, 0) + l['amount_residual']
        
    candidates = []
    for pid, data in pg.items():
        b = data['branches']
        if len(b) > 1 and any(v > 0.01 for v in b.values()) and any(v < -0.01 for v in b.values()):
            candidates.append((pid, data['name'], b))
            
    print(f"Found {len(candidates)} candidates for netting:")
    for c in candidates:
        print(f"Partner {c[0]} ({c[1]}): {c[2]}")

if __name__ == "__main__":
    main()
