
import xmlrpc.client
import argparse
import sys
import logging
import time

# Add the directory containing get_odoo14_credentials to path
import os
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


def migrate_analytic_plans(src_models, src_db, src_uid, src_pass, dest_models, dest_db, dest_uid, dest_pass):
    logger.info("--- Migrating Analytic Plans (from Groups) ---")
    
    # Fetch from Source: Use account.analytic.group for Odoo 14
    src_plans = []
    try:
        # Try finding Plans first (in case it is Odoo 16+)
        src_plan_ids = src_models.execute_kw(src_db, src_uid, src_pass, 'account.analytic.plan', 'search', [[]])
        src_plans = src_models.execute_kw(src_db, src_uid, src_pass, 'account.analytic.plan', 'read', [src_plan_ids], {'fields': ['name', 'description']})
        logger.info(f"Found {len(src_plans)} Plans in source.")
    except Exception:
        # Fallback to Groups (Odoo 14)
        logger.info("No 'account.analytic.plan' in source. Trying 'account.analytic.group'...")
        try:
             grp_ids = src_models.execute_kw(src_db, src_uid, src_pass, 'account.analytic.group', 'search', [[]])
             src_groups = src_models.execute_kw(src_db, src_uid, src_pass, 'account.analytic.group', 'read', [grp_ids], {'fields': ['name', 'description']})
             src_plans = src_groups
             logger.info(f"Found {len(src_plans)} Groups in source (treating as Plans).")
        except Exception as e:
            logger.warning(f"Could not fetch analytic groups or plans: {e}")
            return {}

    plan_mapping = {} # Name -> Dest_ID

    # Ensure a default plan exists if we have accounts without groups
    default_plan_name = "Default"
    
    # Process fetched plans/groups
    all_names = [p['name'] for p in src_plans]
    if default_plan_name not in all_names:
        src_plans.append({'name': default_plan_name, 'description': 'Default Plan for migrated accounts'})

    for plan in src_plans:
        name = plan['name']
        
        # Check in Dest
        dest_plan_ids = dest_models.execute_kw(dest_db, dest_uid, dest_pass, 'account.analytic.plan', 'search', [[('name', '=', name)]])
        
        if dest_plan_ids:
            plan_id = dest_plan_ids[0]
            logger.info(f"Plan '{name}' already exists (ID: {plan_id}).")
        else:
            # Create
            vals = {
                'name': name,
                'description': plan.get('description') or '',
            }
            try:
                plan_id = dest_models.execute_kw(dest_db, dest_uid, dest_pass, 'account.analytic.plan', 'create', [vals])
                logger.info(f"Created Plan '{name}' (ID: {plan_id}).")
            except Exception as e:
                logger.error(f"Failed to create plan '{name}': {e}")
                continue
        
        plan_mapping[name] = plan_id
        
    return plan_mapping

def migrate_analytic_accounts(src_models, src_db, src_uid, src_pass, dest_models, dest_db, dest_uid, dest_pass, plan_mapping):
    logger.info("--- Migrating Analytic Accounts ---")

    # Fetch from Source
    # Determine fields based on version availability
    fields = ['name', 'code', 'partner_id']
    use_plan = False
    use_group = False
    
    # Check fields on source
    try:
        src_fields = src_models.execute_kw(src_db, src_uid, src_pass, 'account.analytic.account', 'fields_get', [], {'attributes': ['name']})
        if 'plan_id' in src_fields:
            fields.append('plan_id')
            use_plan = True
        elif 'group_id' in src_fields:
            fields.append('group_id')
            use_group = True
    except Exception as e:
        logger.error(f"Failed to inspect source fields: {e}")
        return

    try:
        src_acc_ids = src_models.execute_kw(src_db, src_uid, src_pass, 'account.analytic.account', 'search', [[]])
        src_accounts = src_models.execute_kw(src_db, src_uid, src_pass, 'account.analytic.account', 'read', [src_acc_ids], {'fields': fields})
    except Exception as e:
        logger.error(f"Could not fetch analytic accounts from source: {e}")
        return

    count = 0
    default_plan_id = plan_mapping.get("Default")
    
    for acc in src_accounts:
        name = acc['name']
        code = acc.get('code')
        
        # Handle Plan
        plan_id = False
        src_plan_name = None
        
        if use_plan and acc.get('plan_id'):
            src_plan_name = acc['plan_id'][1]
        elif use_group and acc.get('group_id'):
            src_plan_name = acc['group_id'][1]
            
        if src_plan_name and src_plan_name in plan_mapping:
            plan_id = plan_mapping[src_plan_name]
        else:
            plan_id = default_plan_id

        # Check existing in Dest by Name
        domain = [('name', '=', name)]
        
        # Only migrate if we have a plan (mandatory in 19 usually)
        if not plan_id and not default_plan_id:
             # Try to get ANY plan
             if plan_mapping:
                 plan_id = next(iter(plan_mapping.values()))
        
        dest_ids = dest_models.execute_kw(dest_db, dest_uid, dest_pass, 'account.analytic.account', 'search', [domain])
        
        vals = {
            'name': name,
            'code': code or False,
        }
        if plan_id:
            vals['plan_id'] = plan_id
        
        # Partner mapping
        if acc.get('partner_id'):
             src_partner_name = acc['partner_id'][1]
             p_ids = dest_models.execute_kw(dest_db, dest_uid, dest_pass, 'res.partner', 'search', [[('name', '=', src_partner_name)]], {'limit': 1})
             if p_ids:
                 vals['partner_id'] = p_ids[0]

        if dest_ids:
            # Update
            try:
                dest_models.execute_kw(dest_db, dest_uid, dest_pass, 'account.analytic.account', 'write', [[dest_ids[0]], vals])
                logger.info(f"Updated Account '{name}'")
                count += 1
            except Exception as e:
                logger.error(f"Failed to update account '{name}': {e}")
        else:
            # Create
            try:
                new_id = dest_models.execute_kw(dest_db, dest_uid, dest_pass, 'account.analytic.account', 'create', [vals])
                logger.info(f"Created Account '{name}' (ID: {new_id})")
                count += 1
            except Exception as e:
                logger.error(f"Failed to create account '{name}': {e}")

                
    logger.info(f"Processed {count} accounts.")

def main():
    parser = argparse.ArgumentParser(description='Migrate Analytic Accounts from Source to Odoo 19')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Destination Odoo 19 URL')
    parser.add_argument('--db', default='metrodb', help='Destination Odoo 19 DB')
    parser.add_argument('--user', default='admin', help='Destination Odoo 19 User')
    parser.add_argument('--password', default='Amaze@321', help='Destination Odoo 19 Password')
    
    args = parser.parse_args()
    
    # 1. Connect to Destination (Odoo 19)
    logger.info("Connecting to Destination Odoo 19...")
    dest_uid, dest_models = connect_to_odoo(args.url, args.db, args.user, args.password)
    if not dest_uid:
        logger.error("Failed to connect to Destination.")
        return

    # 2. Get Source Credentials
    logger.info("Fetching Source Credentials...")
    creds = get_odoo14_credentials(args.url, args.db, args.user, args.password)
    if not creds:
        logger.error("Could not retrieve source credentials.")
        return

    src_url = creds.get('odoo14_url')
    src_db = creds.get('odoo14_database')
    src_user = creds.get('odoo14_username')
    src_pass = creds.get('odoo14_password')
    
    # 3. Connect to Source
    logger.info(f"Connecting to Source {src_url}...")
    src_uid, src_models = connect_to_odoo(src_url, src_db, src_user, src_pass)
    if not src_uid:
        logger.error("Failed to connect to Source.")
        return

    # 4. Migrate Plans
    plan_map = migrate_analytic_plans(src_models, src_db, src_uid, src_pass, dest_models, args.db, dest_uid, args.password)
    
    # 5. Migrate Matches
    migrate_analytic_accounts(src_models, src_db, src_uid, src_pass, dest_models, args.db, dest_uid, args.password, plan_map)

if __name__ == "__main__":
    main()
