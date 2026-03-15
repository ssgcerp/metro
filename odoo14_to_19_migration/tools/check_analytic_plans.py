import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def check_plans():
    print(f"--- Checking Analytic Plans in Odoo 19 ---")
    plans = models.execute_kw(db, uid, password, 'account.analytic.plan', 'search_read',
        [[]], {'fields': ['id', 'name', 'default_applicability']})
        
    for p in plans:
        print(f"Plan: {p}")
        
    # Also check if 'plan_id' is required on 'account.analytic.account'
    fields = models.execute_kw(db, uid, password, 'account.analytic.account', 'fields_get', 
        ['plan_id'], {'attributes': ['string', 'required']})
    print(f"Plan ID Field: {fields.get('plan_id')}")

if __name__ == "__main__":
    check_plans()
