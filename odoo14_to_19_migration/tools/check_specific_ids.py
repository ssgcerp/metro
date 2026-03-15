import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metro"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def check_ids():
    ctx = {'allowed_company_ids': [1, 2]}
    
    print("Checking Account ID 40 (Original VAT Input)...")
    try:
        acc40 = models.execute_kw(db, uid, password, 'account.account', 'read', [[40], ['name', 'code', 'company_ids']], {'context': ctx})
        if acc40:
            print(f"ID 40: {acc40}")
        else:
            print("ID 40 not found.")
    except Exception as e:
        print(f"Error reading 40: {e}")

    print("\nChecking Account ID 1760 (Created RAK VAT Input)...")
    try:
        acc1760 = models.execute_kw(db, uid, password, 'account.account', 'read', [[1760], ['name', 'code', 'company_ids']], {'context': ctx})
        if acc1760:
            print(f"ID 1760: {acc1760}")
        else:
            print("ID 1760 not found.")
    except Exception as e:
        print(f"Error reading 1760: {e}")

if __name__ == "__main__":
    check_ids()
