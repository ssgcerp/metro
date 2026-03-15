import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def check_trans():
    print(f"--- Checking Translations for Account 1802 ---")
    
    # Check ir.translation for res_id=1802, model=account.account
    trans = models.execute_kw(db, uid, password, 'ir.translation', 'search_read',
        [[('res_id', '=', 1802), ('name', '=', 'account.account,name')]],
        {'fields': ['id', 'lang', 'value', 'src']})
        
    print(f"Found {len(trans)} translations:")
    for t in trans:
        print(f"  {t['lang']}: '{t['src']}' -> '{t['value']}'")

if __name__ == "__main__":
    check_trans()
