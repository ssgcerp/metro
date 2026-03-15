import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metro"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def archive_account():
    BAD_ACCOUNT_ID = 1259
    print(f"Archiving Account {BAD_ACCOUNT_ID}...")
    try:
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[BAD_ACCOUNT_ID], {'active': False, 'name': 'VAT Input (Duplicate - Archived)'}])
        print("Success! Account Archived.")
    except Exception as e:
        print(f"Error archiving: {e}")

    # Verify
    acc = models.execute_kw(db, uid, password, 'account.account', 'read', [[BAD_ACCOUNT_ID], ['active', 'name']])
    if acc:
        print(f"Verification: {acc[0]['name']} Active: {acc[0]['active']}")

if __name__ == "__main__":
    archive_account()
