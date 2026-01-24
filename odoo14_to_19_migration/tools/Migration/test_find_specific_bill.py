
import xmlrpc.client
import argparse
import sys
import logging
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from get_odoo14_credentials import get_odoo14_credentials

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def connect_to_odoo(url, db, username, password):
    try:
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
        uid = common.authenticate(db, username, password, {})
        if uid:
            models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
            return uid, models
    except: pass
    return None, None

def find_specific_line(url, db, user, password):
    creds = get_odoo14_credentials(url, db, user, password)
    if not creds: return
    
    src_url = creds.get('odoo14_url')
    src_db = creds.get('odoo14_database')
    src_user = creds.get('odoo14_username')
    src_pass = creds.get('odoo14_password')
    
    logger.info("Connecting to Source...")
    src_uid, src_models = connect_to_odoo(src_url, src_db, src_user, src_pass)
    
    target_ref = "Roopesh"
    logger.info(f"Searching for Bill with Ref ilike '{target_ref}'...")
    
    try:
        domain = [('ref', 'ilike', target_ref), ('move_type', '=', 'in_invoice')]
        bill_ids = src_models.execute_kw(src_db, src_uid, src_pass, 'account.move', 'search', [domain], {'limit': 5})
        
        if not bill_ids:
            logger.info("NOT FOUND in Source.")
            return

        bills = src_models.execute_kw(src_db, src_uid, src_pass, 'account.move', 'read', [bill_ids], {'fields': ['name', 'ref', 'invoice_line_ids']})
        
        for b in bills:
            logger.info(f"FOUND BILL: {b['name']} | Ref: {b['ref']}")
            # Check lines
            lines = src_models.execute_kw(src_db, src_uid, src_pass, 'account.move.line', 'read', [b['invoice_line_ids']], {'fields': ['name', 'analytic_account_id']})
            for l in lines:
                 logger.info(f" - Line: {l['name'][:30]}... | Analytic: {l['analytic_account_id']}")

    except Exception as e:
        logger.error(f"Error: {e}")
            
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    find_specific_line(args.url, args.db, args.user, args.password)
