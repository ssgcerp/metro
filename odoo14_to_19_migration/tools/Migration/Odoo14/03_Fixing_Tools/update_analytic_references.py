
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
    src_names_clean = {} # Clean name -> Code mapping
    
    import re
    
    for r in s_recs:
        code = r.get('code')
        name = r.get('name', '')
        if code:
            src_map[name] = code
            
            # Create a clean version of the name to handle cases where Odoo 14 had the code in the name
            # e.g., "(PRJ# 0001) Project Name" or "[PRJ# 0001] Project Name"
            clean_name = re.sub(r'^\s*[\(\[].*?[\)\]]\s*', '', name).strip()
            
            # Also handle cases where code might just be prefixed without brackets
            if clean_name.startswith(code):
                clean_name = clean_name[len(code):].strip()
                if clean_name.startswith('-'):
                     clean_name = clean_name[1:].strip()
            
            if clean_name:
                 src_names_clean[clean_name] = code
            
    logger.info(f"Cached {len(src_map)} source accounts with codes.")
    
    # Iterate Destination (only where code is empty)
    logger.info("Updating Destination Accounts...")
    d_domain = ['|', ('code', '=', False), ('code', '=', '')]
    d_ids = d_models.execute_kw(dest_db, d_uid, dest_pass, 'account.analytic.account', 'search', [d_domain])
    d_recs = d_models.execute_kw(dest_db, d_uid, dest_pass, 'account.analytic.account', 'read', [d_ids], {'fields': ['name', 'code']})
    
    updates = 0
    not_found = 0
    for r in d_recs:
        d_name = r.get('name', '')
        d_code = r.get('code')
        
        # 1. Try exact match first
        new_code = src_map.get(d_name)
        
        # 2. Try match against cleaned names
        if not new_code:
            new_code = src_names_clean.get(d_name)
            
        # 3. If dest name has code in it, try to match destination clean name against source clean names
        if not new_code:
             d_clean_name = re.sub(r'^\s*[\(\[].*?[\)\]]\s*', '', d_name).strip()
             new_code = src_names_clean.get(d_clean_name)
             if not new_code:
                 new_code = src_map.get(d_clean_name)

        if new_code:
            if d_code != new_code:
                logger.info(f"Updating '{d_name}': Code '{d_code}' -> '{new_code}'")
                d_models.execute_kw(dest_db, d_uid, dest_pass, 'account.analytic.account', 'write', [[r['id']], {'code': new_code}])
                updates += 1
        else:
            not_found += 1
            # logger.warning(f"Could not find matching source account for '{d_name}' to update code.")

    logger.info(f"Finished. Updated {updates} accounts. {not_found} accounts were not matched.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='newdb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    
    parser.add_argument('--src-url', required=True)
    parser.add_argument('--src-db', required=True)
    parser.add_argument('--src-user', required=True)
    parser.add_argument('--src-password', required=True)
    
    args = parser.parse_args()
    
    update_references(args.url, args.db, args.user, args.password, args.src_url, args.src_db, args.src_user, args.src_password)
