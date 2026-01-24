
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
    
    # Inspect PML 54
    pid = 54
    print(f"Inspecting Payment Method Line {pid}...")
    try:
        data = models.execute_kw(DB, uid, PASS, 'account.payment.method.line', 'read', [[pid]], {'context': {}})[0]
    except Exception as e:
        print(f"Error reading 54: {e}")
        return

    # Print fields
    for k, v in data.items():
         if 'account' in k or 'name' in k:
             print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
