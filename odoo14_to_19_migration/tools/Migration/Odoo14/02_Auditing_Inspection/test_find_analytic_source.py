
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

def find_source_with_analytics(url, db, user, password):
    # Connect
    creds = get_odoo14_credentials(url, db, user, password)
    if not creds: return
    
    src_url = creds.get('odoo14_url')
    src_db = creds.get('odoo14_database')
    src_user = creds.get('odoo14_username')
    src_pass = creds.get('odoo14_password')
    
    logger.info("Connecting to Source...")
    src_uid, src_models = connect_to_odoo(src_url, src_db, src_user, src_pass)
    
    # Search for lines with analytic_account_id != False
    # Limit to recently updated or created
    logger.info("Searching for Source Invoice Lines with Analytics (Newest First)...")
    try:
        # Check fields first
        fields = src_models.execute_kw(src_db, src_uid, src_pass, 'account.move.line', 'fields_get', [], {'attributes': ['string']})
        has_tags = 'analytic_tag_ids' in fields
        
        domain = ['|', ('analytic_account_id', '!=', False)]
        if has_tags:
            domain.append(('analytic_tag_ids', '!=', False))
        else:
            domain = [('analytic_account_id', '!=', False)]
            
        domain.append(('move_id.move_type', '=', 'in_invoice'))
        
        # Search newest first
        line_ids = src_models.execute_kw(src_db, src_uid, src_pass, 'account.move.line', 'search', [domain], {'limit': 20, 'order': 'id desc'})
        
        if not line_ids:
            logger.info("No Vendor Bill lines found with Analytic Account/Tags in Source.")
            return

        read_fields = ['move_id', 'name', 'analytic_account_id']
        if has_tags: read_fields.append('analytic_tag_ids')
        
        lines = src_models.execute_kw(src_db, src_uid, src_pass, 'account.move.line', 'read', [line_ids], {'fields': read_fields})
        
        logger.info(f"Found {len(lines)} sample lines with analytics:")
        for l in lines:
            move_name = l['move_id'][1]
            an_acc = l['analytic_account_id']
            tags = l.get('analytic_tag_ids', [])
            logger.info(f" - Bill: {move_name} | Line: {l['name'][:30]}... | Acc: {an_acc} | Tags: {tags}")
            
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    find_source_with_analytics(args.url, args.db, args.user, args.password)
