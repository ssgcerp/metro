
import xmlrpc.client
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def check_permissions(url, db, user, password):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    # Check if Purchase User can create account.move
    # search for groups
    groups = models.execute_kw(db, uid, password, 'res.groups', 'search_read', [[('name', 'in', ['Purchase User', 'Purchase Administrator', 'Billing', 'Invoicing'])]], {'fields': ['name', 'full_name']})
    
    logger.info("--- Inspecting Groups ---")
    for g in groups:
        logger.info(f"Group: {g['name']} ({g['full_name']})")
        
    # We can't easily Simulate a user here without knowing their login.
    # But we can check Access Control Lists (ir.model.access)
    
    logger.info("\n--- Access Control for account.move ---")
    access_recs = models.execute_kw(db, uid, password, 'ir.model.access', 'search_read', [[('model_id.model', '=', 'account.move'), ('perm_create', '=', True)]], {'fields': ['group_id']})
    
    allowed_groups = []
    for r in access_recs:
        if r['group_id']:
            allowed_groups.append(r['group_id'][1])
            
    logger.info("Groups allowed to CREATE account.move:")
    for gn in sorted(set(allowed_groups)):
        logger.info(f" - {gn}")
        
    # Check specifically if 'Purchase Administrator' is in allowed_groups
    # Note: Using names might be tricky if they vary.
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    check_permissions(args.url, args.db, args.user, args.password)
