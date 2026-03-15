
import xmlrpc.client
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def test_display(url, db, user, password):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    # Create test account
    # Need a plan?
    plans = models.execute_kw(db, uid, password, 'account.analytic.plan', 'search', [[]], {'limit': 1})
    plan_id = plans[0] if plans else False
    
    if not plan_id:
        logger.error("No plan found, cannot create account.")
        return

    vals = {
        'name': 'Test Display Name Project',
        'code': 'TEST001',
        'plan_id': plan_id
    }
    
    logger.info("Creating account with code='TEST001' and name='Test Display Name Project'...")
    new_id = models.execute_kw(db, uid, password, 'account.analytic.account', 'create', [vals])
    
    # Read back display_name
    rec = models.execute_kw(db, uid, password, 'account.analytic.account', 'read', [[new_id]], {'fields': ['display_name']})[0]
    logger.info(f"Result Display Name: '{rec['display_name']}'")
    
    # Cleanup
    # models.execute_kw(db, uid, password, 'account.analytic.account', 'unlink', [[new_id]]) # Maybe keep for inspection or delete? Delete to keep clean.
    models.execute_kw(db, uid, password, 'account.analytic.account', 'unlink', [[new_id]])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    test_display(args.url, args.db, args.user, args.password)
