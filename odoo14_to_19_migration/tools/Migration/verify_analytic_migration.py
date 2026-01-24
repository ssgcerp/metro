
import xmlrpc.client
import argparse
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_migration(url, db, username, password):
    try:
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
        uid = common.authenticate(db, username, password, {})
        if not uid:
            logger.error("Authentication failed")
            return

        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
        
        # Verify "Internal Transfers"
        target_name = "Internal Transfers"
        ids = models.execute_kw(db, uid, password, 'account.analytic.account', 'search', [[('name', '=', target_name)]])
        
        if ids:
            acc = models.execute_kw(db, uid, password, 'account.analytic.account', 'read', [ids], {'fields': ['name', 'plan_id', 'partner_id', 'code']})[0]
            logger.info(f"SUCCESS: Found account '{acc['name']}'")
            logger.info(f"  ID: {acc['id']}")
            logger.info(f"  Plan: {acc.get('plan_id')}")
            logger.info(f"  Partner: {acc.get('partner_id')}")
            logger.info(f"  Code: {acc.get('code')}")
        else:
            logger.error(f"FAILURE: Account '{target_name}' NOT found.")

        # Count total
        total = models.execute_kw(db, uid, password, 'account.analytic.account', 'search_count', [[]])
        logger.info(f"Total Analytic Accounts in Odoo 19: {total}")

    except Exception as e:
        logger.error(f"Verification failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Verify Analytic Migration')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Destination Odoo 19 URL')
    parser.add_argument('--db', default='metrodb', help='Destination Odoo 19 DB')
    parser.add_argument('--user', default='admin', help='Destination Odoo 19 User')
    parser.add_argument('--password', default='Amaze@321', help='Destination Odoo 19 Password')
    
    args = parser.parse_args()
    
    verify_migration(args.url, args.db, args.user, args.password)
