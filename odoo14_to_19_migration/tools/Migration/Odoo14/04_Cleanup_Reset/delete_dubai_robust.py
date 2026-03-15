import xmlrpc.client
import ssl
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
_logger = logging.getLogger(__name__)

URL = 'https://metro.equdaierp.com'
DB = 'newdb'
USER = 'admin'
PWD = 'Amaze@321'
COMPANY_NAME = 'DUBAI'

def safe_execute(models, db, uid, pwd, model, method, args):
    try:
        models.execute_kw(db, uid, pwd, model, method, args)
        return True
    except Exception as e:
        if "marshal None" in str(e):
            return True # Success on server, just client failed to parse None
        _logger.warning(f"  Execution failed for {method} on {model}: {e}")
        return False

def main():
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common', context=ssl._create_unverified_context(), allow_none=True)
    uid = common.authenticate(DB, USER, PWD, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', context=ssl._create_unverified_context(), allow_none=True)
    
    domain = [('company_id.name', '=', COMPANY_NAME), ('partner_type', '=', 'customer'), ('payment_type', '=', 'inbound')]
    pays = models.execute_kw(DB, uid, PWD, 'account.payment', 'search', [domain])
    _logger.info(f"Found {len(pays)} payments to delete.")
    
    for pid in pays:
        # 1. Unreconcile if possible
        # 2. Reset to draft
        safe_execute(models, DB, uid, PWD, 'account.payment', 'action_draft', [[pid]])
        # 3. Cancel
        safe_execute(models, DB, uid, PWD, 'account.payment', 'action_cancel', [[pid]])
        # 4. Unlink
        if safe_execute(models, DB, uid, PWD, 'account.payment', 'unlink', [[pid]]):
            _logger.info(f"  Deleted ID {pid}")

if __name__ == "__main__":
    main()
