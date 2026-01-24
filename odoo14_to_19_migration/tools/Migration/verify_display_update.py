
import xmlrpc.client
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def verify_display(url, db, user, password):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    # Check specifically the ones we likely updated
    # search code = AB 05
    target_code = 'AB 05'
    ids = models.execute_kw(db, uid, password, 'account.analytic.account', 'search', [[('code', '=', target_code)]])
    
    if ids:
        recs = models.execute_kw(db, uid, password, 'account.analytic.account', 'read', [ids], {'fields': ['display_name', 'name', 'code']})
        for r in recs:
            logger.info(f"Record {r['id']}: Display='{r['display_name']}' | Code='{r['code']}' | Name='{r['name']}'")
    else:
        logger.warning(f"No account found with code '{target_code}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    verify_display(args.url, args.db, args.user, args.password)
