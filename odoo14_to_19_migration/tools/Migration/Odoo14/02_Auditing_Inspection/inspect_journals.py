
import xmlrpc.client
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def inspect_journals(url, db, user, password):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    # Get all companies
    companies = models.execute_kw(db, uid, password, 'res.company', 'search_read', [[]], {'fields': ['name']})
    
    for c in companies:
        logger.info(f"\n--- Company: {c['name']} (ID: {c['id']}) ---")
        # Find Vendor Bill Journals
        domain = [('company_id', '=', c['id']), ('type', '=', 'purchase')]
        journals = models.execute_kw(db, uid, password, 'account.journal', 'search_read', [domain], {'fields': ['name', 'code']})
        
        for j in journals:
            # Find last move
            last_move = models.execute_kw(db, uid, password, 'account.move', 'search_read', [[('journal_id', '=', j['id'])]], {'fields': ['name', 'date', 'sequence_prefix'], 'limit': 1, 'order': 'id desc'})
            last_name = last_move[0]['name'] if last_move else "None"
            last_prefix = last_move[0].get('sequence_prefix', 'N/A') if last_move else "N/A"
            logger.info(f"Journal: {j['name']} | Code: {j['code']} | Last Bill: {last_name} | Prefix: {last_prefix}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    inspect_journals(args.url, args.db, args.user, args.password)
