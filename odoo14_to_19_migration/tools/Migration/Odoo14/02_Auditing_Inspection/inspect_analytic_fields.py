
import xmlrpc.client
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def inspect_analytic(url, db, user, password):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    # 1. Get Fields
    fields = models.execute_kw(db, uid, password, 'account.analytic.account', 'fields_get', [], {'attributes': ['string', 'type']})
    logger.info("Fields of account.analytic.account:")
    for f in ['code', 'name', 'partner_id', 'plan_id', 'project_id']:
        if f in fields:
            logger.info(f" - {f}: {fields[f]}")
        else:
            logger.info(f" - {f}: NOT FOUND")
            
    # 2. Check Display Name
    ids = models.execute_kw(db, uid, password, 'account.analytic.account', 'search', [[]], {'limit': 5})
    recs = models.execute_kw(db, uid, password, 'account.analytic.account', 'read', [ids], {'fields': ['display_name', 'name', 'code']})
    
    logger.info("\nSample Records:")
    for r in recs:
        logger.info(f" - Display: '{r['display_name']}' | Name: '{r['name']}' | Code: '{r.get('code')}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    inspect_analytic(args.url, args.db, args.user, args.password)
