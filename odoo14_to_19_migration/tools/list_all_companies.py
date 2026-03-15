import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def list_companies():
    print("--- Listing All Companies ---")
    comps = models.execute_kw(db, uid, password, 'res.company', 'search_read', [], 
        {'fields': ['id', 'name']})
    for c in comps:
        print(f"ID: {c['id']} | Name: {c['name']}")

if __name__ == "__main__":
    list_companies()
