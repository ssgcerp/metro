import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def safe_search(model, domain, fields):
    print(f"  Searching {model}...")
    try:
        res = models.execute_kw(db, uid, password, model, 'search_read', [domain], {'fields': fields, 'limit': 10})
        if res:
            print(f"    FOUND in {model}: {res}")
        else:
            print(f"    No matches in {model}.")
    except Exception as e:
        print(f"    Error searching {model}: {e}")

def final_check_expanded():
    string = "C3TMP"
    print(f"--- Robust Search Explained for '{string}' ---")
    
    # 1. Tax
    safe_search('account.tax', [('name', 'ilike', string)], ['id', 'name'])
    
    # 2. Journal
    safe_search('account.journal', ['|', ('name', 'ilike', string), ('code', 'ilike', string)], ['id', 'name', 'code'])
    
    # 3. Check Account 1802 Group
    print("  Checking Account 1802 Group...")
    acc = models.execute_kw(db, uid, password, 'account.account', 'read', [[1802]], {'fields': ['id', 'group_id']})
    print(f"    Group: {acc[0].get('group_id')}")

if __name__ == "__main__":
    final_check_expanded()
