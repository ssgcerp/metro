import xmlrpc.client
url = "https://metro.equdaierp.com"
db = "newdb"
username = "admin"
password = "Amaze@321"

try:
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

    journals = models.execute_kw(db, uid, password, "account.journal", "read", [[85, 100, 2, 1]], {"fields": ["id", "name", "code", "type", "company_id"]})
    for j in journals:
        print(f"ID: {j['id']} | Name: {j['name']} | Code: {j['code']} | Type: {j['type']} | Company: {j.get('company_id')}")
except Exception as e:
    print(f"Error: {e}")
