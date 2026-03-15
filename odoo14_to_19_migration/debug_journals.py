import xmlrpc.client
url = "https://metro.equdaierp.com"
db_tgt = "newdb"
db_src = "metrodb"
username = "admin"
password = "Amaze@321"

try:
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid_tgt = common.authenticate(db_tgt, username, password, {})
    uid_src = common.authenticate(db_src, username, password, {})
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

    print("\n--- Target Journals (Metro Fire id: 1) ---")
    tgt_journals = models.execute_kw(db_tgt, uid_tgt, password, "account.journal", "search_read", [[("company_id", "=", 1)]], {"fields": ["id", "name", "code", "type"]})
    for j in tgt_journals:
        print(f"{j['id']} | {j['name']} | {j['code']} | {j['type']}")
        
    print("\n--- Source Journals (AJMAN id: 5) ---")
    src_journals = models.execute_kw(db_src, uid_src, password, "account.journal", "search_read", [[("company_id", "=", 5)]], {"fields": ["id", "name", "code", "type"]})
    for j in src_journals:
        print(f"{j['id']} | {j['name']} | {j['code']} | {j['type']}")
    
except Exception as e:
    print(f"Error: {e}")
