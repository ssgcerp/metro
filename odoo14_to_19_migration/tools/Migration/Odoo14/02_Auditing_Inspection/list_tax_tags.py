
import xmlrpc.client
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def list_tax_tags(url, db, user, password):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    # Search for UAE VAT tags
    # Usually named like '1(a)', '1(b)', etc.
    tags = models.execute_kw(db, uid, password, 'account.account.tag', 'search_read', [[]], {'fields': ['name', 'applicability', 'country_id']})
    
    logger.info("--- Tax Tags ---")
    for t in tags:
        if '1(' in t['name']: # Filter for relevant VAT tags
            logger.info(f"Tag: {t['name']} (ID: {t['id']})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    list_tax_tags(args.url, args.db, args.user, args.password)
