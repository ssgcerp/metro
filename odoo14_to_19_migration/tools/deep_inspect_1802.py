import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def deep_inspect():
    string = "201017C3TMP"
    print(f"--- Searching Reports & Inspecting Account 1802 ---")
    
    # 1. Search account.report.line (Odoo 14+ Enterprise)
    try:
        lines = models.execute_kw(db, uid, password, 'account.report.line', 'search_read',
            [[('name', 'ilike', string)]],
            {'fields': ['id', 'name', 'code']})
        print(f"Report Lines: {len(lines)}")
        for l in lines: print(f"  RPT LINE: {l}")
    except Exception as e:
        print(f"No account.report.line or error: {e}")

    # 2. Dump all fields of Account 1802
    acc = models.execute_kw(db, uid, password, 'account.account', 'read', [[1802]], {'context': {'allowed_company_ids': [1, 3]}})
    if acc:
        print("Account 1802 Data:")
        for k, v in acc[0].items():
            if v and str(v) != 'False':
                print(f"  {k}: {v}")

if __name__ == "__main__":
    deep_inspect()
