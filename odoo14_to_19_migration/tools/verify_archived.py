import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metro"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def verify():
    BAD_ACCOUNT_ID = 1259
    acc = models.execute_kw(db, uid, password, 'account.account', 'read', [[BAD_ACCOUNT_ID], ['active', 'name']])
    if acc:
        print(f"Account {acc[0]['name']} Active: {acc[0]['active']}")
    else:
        print("Account not found (maybe deleted?)")

if __name__ == "__main__":
    verify()
