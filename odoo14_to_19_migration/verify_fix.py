
import xmlrpc.client
import ssl

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url), context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url), context=ssl._create_unverified_context())

bills = [
    "BILL/2025/02/0052", "BILL/2025/02/0053", "BILL/2025/08/0135", 
    "BILL/2025/09/0156", "BILL/2025/09/0157", "EXP/2025/01/0376", 
    "EXP/2025/08/0215", "EXP/2025/09/0439", "EXP/2025/10/0205"
]

print("-" * 80)
print(f"{'Bill Name':<20} | {'State':<10} | {'Company':<30} | {'Status'}")
print("-" * 80)

for b in bills:
    recs = models.execute_kw(db, uid, password, 'account.move', 'search_read', [[['name', '=', b]]], {'fields': ['name', 'state', 'company_id']})
    if recs:
        rec = recs[0]
        comp_name = rec['company_id'][1]
        status = "OK" if "ABU DHABI" in comp_name else "WRONG"
        print(f"{rec['name']:<20} | {rec['state']:<10} | {comp_name:<30} | {status}")
    else:
        print(f"{b:<20} | {'N/A':<10} | {'Not Found':<30} | MISSING")
print("-" * 80)
