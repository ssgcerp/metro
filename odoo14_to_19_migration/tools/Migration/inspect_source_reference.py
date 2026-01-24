
import xmlrpc.client
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def inspect_ref(url, db, user, password):
    logger.info(f"Connecting to {url}...")
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    if not uid:
        logger.error("Auth failed")
        return
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    target_val = "PRJ# 00779"
    logger.info(f"Searching for account with value '{target_val}' in any field...")
    
    # search by name just to find the record first, seeing the screenshot
    # Name: "AG - Sonapur Refilling" (from screenshot 0, first row matches ref PRJ# 00779)
    # Actually, let's search by name "AG - Sonapur Refilling"
    name_target = "AG - Sonapur Refilling"
    
    ids = models.execute_kw(db, uid, password, 'account.analytic.account', 'search', [[('name', '=', name_target)]])
    
    if not ids:
        logger.warning(f"Record with name '{name_target}' not found. Trying ilike...")
        ids = models.execute_kw(db, uid, password, 'account.analytic.account', 'search', [[('name', 'ilike', 'Sonapur')]])
        
    if ids:
        # Read all fields for the first match
        fields = models.execute_kw(db, uid, password, 'account.analytic.account', 'fields_get', [], {'attributes': ['string', 'type']})
        field_names = list(fields.keys())
        
        recs = models.execute_kw(db, uid, password, 'account.analytic.account', 'read', [ids], {'fields': field_names})
        
        for r in recs:
            logger.info(f"Checking Record ID {r['id']} ({r['name']}):")
            found_field = False
            for k, v in r.items():
                if str(v) == target_val:
                    logger.info(f" !!! FOUND MATCH !!! Field '{k}' = '{v}'")
                    found_field = True
            
            if not found_field:
                logger.info(f"Target value '{target_val}' not found in any top-level field. Dumping relevant fields:")
                for k in ['code', 'ref', 'reference', 'display_name']:
                    if k in r:
                        logger.info(f" - {k}: {r[k]}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--db', required=True)
    parser.add_argument('--user', required=True)
    parser.add_argument('--password', required=True)
    args = parser.parse_args()
    
    inspect_ref(args.url, args.db, args.user, args.password)
