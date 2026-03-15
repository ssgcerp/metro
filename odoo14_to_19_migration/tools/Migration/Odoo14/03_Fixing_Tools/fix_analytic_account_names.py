
import xmlrpc.client
import argparse
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def fix_names(url, db, user, password):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    # regex for (Code) Name
    # Matches starting with (something) space...
    pattern = re.compile(r'^\(([^)]+)\)\s*(.*)')
    
    ids = models.execute_kw(db, uid, password, 'account.analytic.account', 'search', [[]])
    recs = models.execute_kw(db, uid, password, 'account.analytic.account', 'read', [ids], {'fields': ['name', 'code']})
    
    logger.info(f"Processing {len(recs)} accounts...")
    
    updates = 0
    for r in recs:
        name = r['name']
        current_code = r['code']
        
        # Check if name is False (shouldn't be)
        if not name: continue
        
        match = pattern.match(name)
        if match:
            extracted_code = match.group(1).strip()
            new_name = match.group(2).strip()
            
            # Update only if code is empty or we want to force it?
            # Let's assume we populate code if empty.
            # If code matches extracted, just clean name.
            
            vals = {}
            if not current_code:
                vals['code'] = extracted_code
                vals['name'] = new_name
            elif current_code == extracted_code:
                # Code exists and matches, just clean name
                vals['name'] = new_name
            else:
                # Code exists but differs?
                # Maybe assume the name has the 'Project Code' logic from source 
                # and we should prefer it?
                # For safety, let's log warning and optional update.
                logger.warning(f"Skipping {r['id']}: '{name}' has code '{extracted_code}' but current code field is '{current_code}'")
                continue
                
            logger.info(f"Updating {r['id']}: Code='{extracted_code}', Name='{new_name}' (Was: '{name}')")
            models.execute_kw(db, uid, password, 'account.analytic.account', 'write', [[r['id']], vals])
            updates += 1
            
    logger.info(f"Finished. Updated {updates} accounts.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='newdb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    fix_names(args.url, args.db, args.user, args.password)
