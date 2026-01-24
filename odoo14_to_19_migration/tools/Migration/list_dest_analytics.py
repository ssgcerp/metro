
import xmlrpc.client
import argparse
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def list_analytics(url, db, user, password):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    ids = models.execute_kw(db, uid, password, 'account.analytic.account', 'search', [[]])
    recs = models.execute_kw(db, uid, password, 'account.analytic.account', 'read', [ids], {'fields': ['name', 'code']})
    
    logger.info(f"Found {len(recs)} accounts in Dest:")
    for r in recs:
        logger.info(f" - {r['name']} (Code: {r['code']})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    list_analytics(args.url, args.db, args.user, args.password)
