import xmlrpc.client
import json

url = "https://metro.equdaierp.com"
db = "metro"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def check_clear():
    ctx = {'allowed_company_ids': [1, 2]}
    
    print("--- Reading ID 40 ---")
    try:
        acc40 = models.execute_kw(db, uid, password, 'account.account', 'read', [[40], ['name', 'code', 'company_ids']], {'context': ctx})
        print(json.dumps(acc40, indent=2))
    except Exception as e:
        print(f"Error 40: {e}")

    print("\n--- Reading ID 1760 ---")
    try:
        acc1760 = models.execute_kw(db, uid, password, 'account.account', 'read', [[1760], ['name', 'code', 'company_ids']], {'context': ctx})
        print(json.dumps(acc1760, indent=2))
    except Exception as e:
        print(f"Error 1760: {e}")

    print("\n--- Reading ID 1761 (VAT Output) ---")
    try:
        acc1761 = models.execute_kw(db, uid, password, 'account.account', 'read', [[1761], ['name', 'code', 'company_ids']], {'context': ctx})
        print(json.dumps(acc1761, indent=2))
    except Exception as e:
        print(f"Error 1761: {e}")

if __name__ == "__main__":
    check_clear()
