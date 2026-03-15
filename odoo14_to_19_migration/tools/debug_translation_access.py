import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def debug_models():
    print(f"--- Checking Model Access ---")
    
    # Check if we can search ir.model
    try:
        res = models.execute_kw(db, uid, password, 'ir.model', 'search', [[('model', '=', 'ir.translation')]])
        print(f"ir.translation model ID: {res}")
    except Exception as e:
        print(f"Error searching ir.model: {e}")

    # Check account.account fields for name
    fields = models.execute_kw(db, uid, password, 'account.account', 'fields_get', [['name']], {'attributes': ['translate']})
    print(f"Account Name Field: {fields}")

if __name__ == "__main__":
    debug_models()
