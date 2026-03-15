import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def revert_fix():
    print(f"--- Reverting Account 1802 to '201017' ---")
    ctx = {'allowed_company_ids': [1, 3]}
    models.execute_kw(db, uid, password, 'account.account', 'write',
        [[1802], {'code': '201017', 'name': 'VAT Output'}],
        {'context': ctx})
    print("Revert complete.")

if __name__ == "__main__":
    revert_fix()
