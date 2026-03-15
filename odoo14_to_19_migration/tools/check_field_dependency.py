import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def check_field():
    print(f"--- Checking 'code' field on account.account ---")
    
    fields = models.execute_kw(db, uid, password, 'account.account', 'fields_get', 
        [['code'], ['company_dependent', 'type', 'string']],
        {'context': {'allowed_company_ids': [1]}})
        
    print(f"Field Info: {fields}")

if __name__ == "__main__":
    check_field()
