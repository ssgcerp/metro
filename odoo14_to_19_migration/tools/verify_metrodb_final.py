import xmlrpc.client
import json

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def verify_metrodb():
    ctx = {'allowed_company_ids': [1, 2]}
    print(f"--- Verifying RAK VAT Accounts in {db} ---")
    
    # Check VAT Input
    vat_in = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', '=', '104041'), ('company_ids', 'in', [2])]],
        {'fields': ['id', 'name', 'code', 'company_ids'], 'context': ctx})
    print("VAT Input 104041:", json.dumps(vat_in, indent=2))

    # Check VAT Output
    vat_out = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', '=', '201017'), ('company_ids', 'in', [2])]],
        {'fields': ['id', 'name', 'code', 'company_ids'], 'context': ctx})
    print("VAT Output 201017:", json.dumps(vat_out, indent=2))

if __name__ == "__main__":
    verify_metrodb()
