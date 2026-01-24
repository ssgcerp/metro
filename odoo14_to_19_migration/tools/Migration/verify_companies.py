
import xmlrpc.client
import argparse
import sys
import logging
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from get_odoo14_credentials import get_odoo14_credentials

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def connect_to_odoo(url, db, username, password):
    try:
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
        uid = common.authenticate(db, username, password, {})
        if uid:
            models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
            return uid, models
    except Exception as e:
        logger.error(f"Connect Error {url}: {e}")
    return None, None

def check_companies_and_bills(url, db, user, password):
    # 1. Dest
    logger.info(f"--- DESTINATION: {url} ---")
    d_uid, d_models = connect_to_odoo(url, db, user, password)
    if not d_uid: return

    d_companies = d_models.execute_kw(db, d_uid, password, 'res.company', 'search_read', [[]], {'fields': ['name']})
    for c in d_companies:
        # Count bills
        count = d_models.execute_kw(db, d_uid, password, 'account.move', 'search_count', [[('move_type', '=', 'in_invoice'), ('company_id', '=', c['id'])]])
        # Count bills with analytic distribution
        # This might be slow if we search on JSON field, but let's try searching on line level?
        # Domain on JSON field is tricky in Odoo.
        # Approximation: Check total analytics count for this company? No, irrelevant.
        logger.info(f"[ID: {c['id']}] {c['name']} - Bills: {count}")

    # 2. Source
    creds = get_odoo14_credentials(url, db, user, password)
    if not creds: return
    
    src_url = creds.get('odoo14_url')
    src_db = creds.get('odoo14_database')
    src_user = creds.get('odoo14_username')
    src_pass = creds.get('odoo14_password')
    
    logger.info(f"\n--- SOURCE: {src_url} ---")
    s_uid, s_models = connect_to_odoo(src_url, src_db, src_user, src_pass)
    if not s_uid: return

    try:
        s_companies = s_models.execute_kw(src_db, s_uid, src_pass, 'res.company', 'search_read', [[]], {'fields': ['name']})
        for c in s_companies:
            count = s_models.execute_kw(src_db, s_uid, src_pass, 'account.move', 'search_count', [[('move_type', '=', 'in_invoice'), ('company_id', '=', c['id'])]])
            logger.info(f"[ID: {c['id']}] {c['name']} - Bills: {count}")
    except Exception as e:
        logger.error(f"Error reading source companies: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    check_companies_and_bills(args.url, args.db, args.user, args.password)
