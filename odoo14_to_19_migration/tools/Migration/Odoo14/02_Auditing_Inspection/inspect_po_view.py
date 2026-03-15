
import xmlrpc.client
import argparse
import logging
from pprint import pprint

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def inspect_view(url, db, user, password):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    # Get the default form view for purchase.order
    # We can try to find the specific view if we knew the ID, but let's get the one used by default
    res = models.execute_kw(db, uid, password, 'purchase.order', 'get_view', [], {'view_type': 'form'})
    
    logger.info("--- View Architecture Inspection ---")
    logger.info(f"View ID: {res.get('id')}")
    arch = res.get('arch')
    
    if 'action_create_invoice' in arch:
        logger.info("SUCCESS: 'action_create_invoice' button FOUND in arch.")
        # Try to extract the line
        for line in arch.split('\n'):
            if 'action_create_invoice' in line:
                logger.info(f"Button Line: {line.strip()}")
    else:
        logger.error("FAILURE: 'action_create_invoice' button NOT FOUND in arch.")
        
    # Check model permissions
    access = models.execute_kw(db, uid, password, 'purchase.order', 'check_access_rights', ['write'], {'raise_exception': False})
    logger.info(f"User Write Access to PO: {access}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    inspect_view(args.url, args.db, args.user, args.password)
