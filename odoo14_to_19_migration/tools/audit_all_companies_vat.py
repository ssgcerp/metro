import xmlrpc.client
import json

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def audit_companies():
    print(f"--- Auditing VAT Accounts in {db} ---")
    
    # Get all companies
    companies = models.execute_kw(db, uid, password, 'res.company', 'search_read',
        [[]], {'fields': ['id', 'name']})
        
    print(f"Found {len(companies)} companies.")
    
    ctx_admin = {'allowed_company_ids': [c['id'] for c in companies]}
    
    for comp in companies:
        cid = comp['id']
        cname = comp['name']
        print(f"\n[{cid}] {cname}")
        
        ctx = {'allowed_company_ids': [1, cid]}
        
        # Check VAT Input
        vat_in = models.execute_kw(db, uid, password, 'account.account', 'search_read',
            [[('code', '=', '104041'), ('company_ids', 'in', [cid])]],
            {'fields': ['id', 'name', 'code'], 'context': ctx})
            
        status_in = "OK" if vat_in else "MISSING"
        print(f"  VAT Input (104041): {status_in} {vat_in if vat_in else ''}")
        
        # Check VAT Output
        vat_out = models.execute_kw(db, uid, password, 'account.account', 'search_read',
            [[('code', '=', '201017'), ('company_ids', 'in', [cid])]],
            {'fields': ['id', 'name', 'code'], 'context': ctx})
            
        status_out = "OK" if vat_out else "MISSING"
        print(f"  VAT Output (201017): {status_out} {vat_out if vat_out else ''}")
        
        # Check for Lost Entries (only check if status is MISSING or strictly suspicious)
        # We check for lines with 'VAT' in name on WRONG accounts
        vat_ids = []
        if vat_in: vat_ids.append(vat_in[0]['id'])
        if vat_out: vat_ids.append(vat_out[0]['id'])
        
        # Exclude specific known VAT accounts if any
        # (This is just a heuristic count)
        count_lost = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
            [[('company_id', '=', cid), ('name', 'ilike', 'VAT'), ('account_id', 'not in', vat_ids)]],
            {'context': ctx})
            
        if count_lost > 0:
            print(f"  WARNING: {count_lost} potential lost 'VAT' entries found on other accounts.")

if __name__ == "__main__":
    audit_companies()
