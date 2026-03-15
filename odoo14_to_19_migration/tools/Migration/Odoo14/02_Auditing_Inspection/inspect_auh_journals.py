
import xmlrpc.client
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def inspect_auh_journals(url, db, user, password):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    # Abu Dhabi ID = 1
    cid = 1
    
    journals = models.execute_kw(db, uid, password, 'account.journal', 'search_read', [[('company_id', '=', cid)]], {'fields': ['name', 'type', 'code']})
    
    logger.info("--- Journals in Abu Dhabi (ID: 1) ---")
    pos_journals = []
    for j in journals:
        logger.info(f"Journal: {j['name']} ({j['type']}) Code: {j['code']}")
        if j['type'] == 'sale' or 'POS' in j['name']:
            pos_journals.append(j['name'])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    inspect_auh_journals(args.url, args.db, args.user, args.password)
