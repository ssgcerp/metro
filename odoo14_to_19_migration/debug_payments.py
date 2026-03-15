import xmlrpc.client
url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

try:
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

    print(f"Logged in as UID: {uid}")

    print("\n--- Searching for ANY payments in metrodb (limit 5) ---")
    payments = models.execute_kw(db, uid, password, "account.payment", "search_read", [[]], {"limit": 5, "fields": ["id", "name", "state", "company_id"]})
    for p in payments:
        print(p)
        
    print("\n--- Searching for AJMAN (company_id 5) payments ---")
    payments_ajman = models.execute_kw(db, uid, password, "account.payment", "search_read", [[("company_id", "=", 5)]], {"limit": 5, "fields": ["id", "name", "state"]})
    for p in payments_ajman:
        print(p)
        
    all_ajman = models.execute_kw(db, uid, password, "account.payment", "search", [[("company_id", "=", 5)]])
    print(f"\nTotal AJMAN payments found: {len(all_ajman)}")

    posted_ajman = models.execute_kw(db, uid, password, "account.payment", "search", [[("company_id", "=", 5), ("state", "=", "posted")]])
    print(f"Total Posted AJMAN payments found: {len(posted_ajman)}")
    
except Exception as e:
    print(f"Error: {e}")
