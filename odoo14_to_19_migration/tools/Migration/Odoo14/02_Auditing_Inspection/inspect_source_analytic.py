
import xmlrpc.client
import argparse
import sys
import logging
import os

# Add the directory containing get_odoo14_credentials to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from get_odoo14_credentials import get_odoo14_credentials

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def connect_to_odoo(url, db, username, password):
    try:
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
        uid = common.authenticate(db, username, password, {})
        if uid:
            models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
            return uid, models
        else:
            return None, None
    except Exception as e:
        logger.error(f"Connection failed to {url}: {e}")
        return None, None

def inspect_source(url, db, user, password):
    logger.info("Fetching Source Credentials...")
    creds = get_odoo14_credentials(url, db, user, password)
    if not creds:
        logger.error("Could not retrieve source credentials.")
        return

    src_url = creds.get('odoo14_url')
    src_db = creds.get('odoo14_database')
    src_user = creds.get('odoo14_username')
    src_pass = creds.get('odoo14_password')
    
    logger.info(f"Connecting to Source {src_url}...")
    src_uid, src_models = connect_to_odoo(src_url, src_db, src_user, src_pass)
    
    target = "Internal Transfers"
    logger.info(f"Searching for '{target}' in Source...")
    
    # 1. Analytic Accounts
    try:
        ids = src_models.execute_kw(src_db, src_uid, src_pass, 'account.analytic.account', 'search', [[('name', 'ilike', target)]])
        if ids:
            accs = src_models.execute_kw(src_db, src_uid, src_pass, 'account.analytic.account', 'read', [ids], {'fields': ['name', 'code', 'partner_id', 'group_id']})
            logger.info(f"FOUND in account.analytic.account: {accs}")
        else:
            logger.info(f"NOT FOUND in account.analytic.account")
    except Exception as e:
        logger.error(f"Error searching accounts: {e}")

    # 2. Analytic Groups
    try:
        ids = src_models.execute_kw(src_db, src_uid, src_pass, 'account.analytic.group', 'search', [[('name', 'ilike', target)]])
        if ids:
            grps = src_models.execute_kw(src_db, src_uid, src_pass, 'account.analytic.group', 'read', [ids], {'fields': ['name', 'description']})
            logger.info(f"FOUND in account.analytic.group: {grps}")
        else:
            logger.info(f"NOT FOUND in account.analytic.group")
    except Exception as e:
        logger.error(f"Error searching groups: {e}")
        
    # 3. Analytic Plans (if exists)
    try:
        ids = src_models.execute_kw(src_db, src_uid, src_pass, 'account.analytic.plan', 'search', [[('name', 'ilike', target)]])
        if ids:
            plans = src_models.execute_kw(src_db, src_uid, src_pass, 'account.analytic.plan', 'read', [ids], {'fields': ['name']})
            logger.info(f"FOUND in account.analytic.plan: {plans}")
        else:
             logger.info(f"NOT FOUND in account.analytic.plan")
    except Exception:
        logger.info("account.analytic.plan model does not exist in source.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Inspect Source for Analytic Record')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Destination Odoo 19 URL')
    parser.add_argument('--db', default='metrodb', help='Destination Odoo 19 DB')
    parser.add_argument('--user', default='admin', help='Destination Odoo 19 User')
    parser.add_argument('--password', default='Amaze@321', help='Destination Odoo 19 Password')
    
    args = parser.parse_args()
    inspect_source(args.url, args.db, args.user, args.password)
