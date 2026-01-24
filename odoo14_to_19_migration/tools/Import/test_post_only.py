
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
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
    
    pid = 9394
    print(f"Posting Payment {pid}...")
    try:
        models.execute_kw(DB, uid, PASS, 'account.payment', 'action_post', [[pid]])
        print("Post executed.")
    except Exception as e:
        print(f"Post FAILED: {e}")
        
    # Check
    data = models.execute_kw(DB, uid, PASS, 'account.payment', 'read', [[pid], ['state', 'outstanding_account_id']])[0]
    print(f"Result: {data}")

if __name__ == "__main__":
    main()
