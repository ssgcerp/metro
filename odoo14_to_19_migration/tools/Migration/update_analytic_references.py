
import xmlrpc.client
import argparse
import logging

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

def update_references(dest_url, dest_db, dest_user, dest_pass, src_url, src_db, src_user, src_pass):
    # Connect
    logger.info("Connecting to Destination...")
    d_uid, d_models = connect_to_odoo(dest_url, dest_db, dest_user, dest_pass)
    logger.info("Connecting to Source...")
    s_uid, s_models = connect_to_odoo(src_url, src_db, src_user, src_pass)
    
    if not d_uid or not s_uid:
        logger.error("Connection failed.")
        return

    # Cache Source Accounts: Name -> Code
    logger.info("Caching Source Data...")
    s_ids = s_models.execute_kw(src_db, s_uid, src_pass, 'account.analytic.account', 'search', [[]])
    s_recs = s_models.execute_kw(src_db, s_uid, src_pass, 'account.analytic.account', 'read', [s_ids], {'fields': ['name', 'code']})
    
    src_map = {}
    for r in s_recs:
        if r['code']: # Only cache if code exists
            src_map[r['name']] = r['code']
            
    logger.info(f"Cached {len(src_map)} source accounts with codes.")
    
    # Iterate Destination
    logger.info("Updating Destination Accounts...")
    d_ids = d_models.execute_kw(dest_db, d_uid, dest_pass, 'account.analytic.account', 'search', [[]])
    d_recs = d_models.execute_kw(dest_db, d_uid, dest_pass, 'account.analytic.account', 'read', [d_ids], {'fields': ['name', 'code']})
    
    updates = 0
    for r in d_recs:
        d_name = r['name']
        d_code = r.get('code')
        
        # Check against clean name (in case it already has [Code] prefix handling from previous steps?
        # Actually my previous fix extracted code from name. 
        # But if the name in Source matches "Name" part, we are good.
        # If Destination name matches Source name exactly, we map.
        
        # Let's try exact match first.
        
        new_code = src_map.get(d_name)
        
        if new_code:
            if d_code != new_code:
                logger.info(f"Updating '{d_name}': Code '{d_code}' -> '{new_code}'")
                d_models.execute_kw(dest_db, d_uid, dest_pass, 'account.analytic.account', 'write', [[r['id']], {'code': new_code}])
                updates += 1
            else:
                # Already correct
                pass
        else:
            # Handle case where Destination Name might have changed? 
            # Or if my previous fix modified the name? 
            # "fix_analytic_account_names.py" changed "(Code) Name" -> "Name". 
            # If Source name was "Name", it should match.
            # If Source name was "(Code) Name", then my previous fix standardized the Dest name to "Name".
            # BUT: inspect_source_reference.py showed Source Name is "AG - Sonapur Refilling" (No code in name).
            # So Source Name == Clean Dest Name. Match should work.
            pass

    logger.info(f"Finished. Updated {updates} accounts.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    
    parser.add_argument('--src-url', required=True)
    parser.add_argument('--src-db', required=True)
    parser.add_argument('--src-user', required=True)
    parser.add_argument('--src-password', required=True)
    
    args = parser.parse_args()
    
    update_references(args.url, args.db, args.user, args.password, args.src_url, args.src_db, args.src_user, args.src_password)
