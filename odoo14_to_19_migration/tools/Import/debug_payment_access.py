
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print("Connecting...")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    if not uid:
        print("Auth failed.")
        return
    
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    # Check User Companies
    user_info = models.execute_kw(DB, uid, PASS, 'res.users', 'read', [[uid], ['company_ids', 'company_id']])
    print(f"User Info: {user_info}")
    
    # 1. Fetch All Companies
    companies = models.execute_kw(DB, uid, PASS, 'res.company', 'search', [[]])
    print(f"Found Companies: {companies}")
    
    ctx = {'allowed_company_ids': companies}
    print(f"Using Context: {ctx}")
    
    # 2. Search Payments
    domain = [('state', '=', 'draft'), ('partner_type', '=', 'supplier')]
    p_ids = models.execute_kw(DB, uid, PASS, 'account.payment', 'search', [domain], {'limit': 5, 'context': ctx})
    print(f"Found Payments: {p_ids}")
    
    if p_ids:
        # 3. Read ONE
        pid = p_ids[0]
        print(f"Attempting to READ {pid}...")
        try:
            data = models.execute_kw(DB, uid, PASS, 'account.payment', 'read', [[pid], ['name', 'company_id']], {'context': ctx})
            print(f"Read Result: {data}")
        except Exception as e:
            print(f"Read Error: {e}")

if __name__ == "__main__":
    main()
