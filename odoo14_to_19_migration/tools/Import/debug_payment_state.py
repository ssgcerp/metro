
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print("Connecting...")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    # Search for ANY supplier payment
    # Inspect 9419 and 9811
    ids = [9419, 9811]
    print(f"Inspecting {ids}...")
    res = models.execute_kw(DB, uid, PASS, 'account.payment', 'read', [ids, ['name', 'journal_id', 'payment_method_line_id', 'outstanding_account_id', 'state']], {'context': {}})
    for r in res:
        print(r)
        return

if __name__ == "__main__":
    main()
