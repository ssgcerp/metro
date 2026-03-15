import xmlrpc.client
import ssl
import time

URL = 'https://metro.equdaierp.com'
DB = 'newdb'
USER = 'admin'
PWD = 'Amaze@321'
COMPANY_NAME = 'DUBAI'

def main():
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common', context=ssl._create_unverified_context(), allow_none=True)
    uid = common.authenticate(DB, USER, PWD, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', context=ssl._create_unverified_context(), allow_none=True)
    
    domain = [('company_id.name', '=', COMPANY_NAME), ('partner_type', '=', 'customer'), ('payment_type', '=', 'inbound')]
    pays = models.execute_kw(DB, uid, PWD, 'account.payment', 'search', [domain])
    print(f"Found {len(pays)} payments to delete.")
    
    for pid in pays:
        try:
            # Try to cancel it first to make it deletable
            models.execute_kw(DB, uid, PWD, 'account.payment', 'action_draft', [[pid]])
            models.execute_kw(DB, uid, PWD, 'account.payment', 'action_cancel', [[pid]])
            models.execute_kw(DB, uid, PWD, 'account.payment', 'unlink', [[pid]])
            print(f"Deleted ID {pid}")
        except Exception as e:
            print(f"Failed ID {pid}: {e}")

if __name__ == "__main__":
    main()
