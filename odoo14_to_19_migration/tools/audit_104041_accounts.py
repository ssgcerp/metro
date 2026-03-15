import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

ALL_COMPANIES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
MASTER_ID = 744

def audit():
    print("--- Auditing ALL 104041 Accounts (including archived) ---")
    ctx = {'allowed_company_ids': ALL_COMPANIES, 'active_test': False}
    
    accs = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', 'like', '104041')]],
        {'fields': ['id', 'name', 'code', 'active', 'company_ids'], 'context': ctx})
    
    with open('audit_104041.txt', 'w', encoding='utf-8') as f:
        f.write(f"Found {len(accs)} accounts with code like '104041':\n")
        for a in accs:
            line_count = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
                [[('account_id', '=', a['id'])]])
            f.write(f"  ID {a['id']} | Code: {a['code']} | Active: {a['active']} | Companies: {a['company_ids']} | Lines: {line_count}\n")
            f.write(f"    Name: {a['name']}\n")
    print("Written to audit_104041.txt")

if __name__ == "__main__":
    audit()
