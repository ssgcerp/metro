
import xmlrpc.client
import argparse
import sys
import logging
import os

# Add the directory containing get_odoo14_credentials to path
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


def fix_bill_analytics(dest_url, dest_db, dest_user, dest_pass, src_url, src_db, src_user, src_pass):
    # 1. Connect to Destination
    logger.info("Connecting to Destination Odoo 19...")
    dest_uid, dest_models = connect_to_odoo(dest_url, dest_db, dest_user, dest_pass)
    if not dest_uid: return

    # 2. Connect to Source (Explicit)
    logger.info(f"Connecting to Source {src_url}...")
    src_uid, src_models = connect_to_odoo(src_url, src_db, src_user, src_pass)
    if not src_uid: 
        logger.error("Failed to connect to Source.")
        return

    # 3. Cache Destination Analytic Accounts (Name -> ID)
    logger.info("Caching Destination Analytic Accounts...")
    try:
        aa_ids = dest_models.execute_kw(dest_db, dest_uid, dest_pass, 'account.analytic.account', 'search', [[]])
        aa_data = dest_models.execute_kw(dest_db, dest_uid, dest_pass, 'account.analytic.account', 'read', [aa_ids], {'fields': ['name']})
        dest_map_name_to_id = {rec['name']: rec['id'] for rec in aa_data}
        logger.info(f"Cached {len(dest_map_name_to_id)} destination analytic accounts.")
    except Exception as e:
        logger.error(f"Failed to cache dest analytic accounts: {e}")
        return

    # 4. Cache Source Analytic Accounts (ID -> Name)
    logger.info("Caching Source Analytic Accounts...")
    try:
        s_aa_ids = src_models.execute_kw(src_db, src_uid, src_pass, 'account.analytic.account', 'search', [[]])
        s_aa_data = src_models.execute_kw(src_db, src_uid, src_pass, 'account.analytic.account', 'read', [s_aa_ids], {'fields': ['name']})
        src_map_id_to_name = {str(rec['id']): rec['name'] for rec in s_aa_data} # Key as string for JSON matching
        logger.info(f"Cached {len(src_map_id_to_name)} source analytic accounts.")
    except Exception as e:
        logger.error(f"Failed to cache source analytic accounts: {e}")
        return

    # 5. Fetch Destination Bills
    logger.info("Fetching Vendor Bills from Destination...")
    try:
        bill_ids = dest_models.execute_kw(dest_db, dest_uid, dest_pass, 'account.move', 'search', [[('move_type', '=', 'in_invoice')]]) 
        bill_ids.sort(reverse=True) # Newest first
        logger.info(f"Found {len(bill_ids)} bills to check. Processing newest first.")
    except Exception as e:
        logger.error(f"Failed to search bills: {e}")
        return

    count_updated = 0
    count_processed = 0
    
    for bill_id in bill_ids:
        count_processed += 1
        if count_processed % 50 == 0:
            logger.info(f"Processed {count_processed}/{len(bill_ids)} bills...")

        try:
            # Read Dest Bill
            bill = dest_models.execute_kw(dest_db, dest_uid, dest_pass, 'account.move', 'read', [[bill_id], ['name', 'ref', 'invoice_line_ids']])
            if not bill: continue
            bill = bill[0]
            
            bill_name = bill['name']
            
            # Find Source Bill
            # Match strictly by Name first
            # Search order: Name -> Ref (if needed)
            src_domain = [('name', '=', bill_name), ('move_type', '=', 'in_invoice')]
            src_bill_ids = src_models.execute_kw(src_db, src_uid, src_pass, 'account.move', 'search', [src_domain])
            
            if not src_bill_ids:
                continue
            
            # Read Source Bill Header to get lines
            src_bill_data = src_models.execute_kw(src_db, src_uid, src_pass, 'account.move', 'read', [src_bill_ids], {'fields': ['invoice_line_ids']})
            if not src_bill_data: continue
            
            src_line_ids = src_bill_data[0]['invoice_line_ids']
            
            # Read Source Lines
            src_lines = src_models.execute_kw(src_db, src_uid, src_pass, 'account.move.line', 'read', [src_line_ids], {'fields': ['name', 'analytic_distribution']})
            
            dest_line_ids = bill['invoice_line_ids']
            dest_lines = dest_models.execute_kw(dest_db, dest_uid, dest_pass, 'account.move.line', 'read', [dest_line_ids], {'fields': ['name', 'analytic_distribution']})
            
            if len(src_lines) != len(dest_lines):
                 # logger.warning(f"Line count mismatch for {bill_name}: Src={len(src_lines)}, Dest={len(dest_lines)}.")
                 continue

            lines_to_update = []
            
            for i in range(len(src_lines)):
                s_line = src_lines[i]
                d_line = dest_lines[i]
                
                dist_raw = s_line.get('analytic_distribution')
                if dist_raw:
                    # dist_raw is {'id': percentage} e.g. {'7': 100.0}
                    new_dist = {}
                    
                    for s_id_str, percent in dist_raw.items():
                        s_name = src_map_id_to_name.get(s_id_str)
                        if s_name:
                            d_id = dest_map_name_to_id.get(s_name)
                            
                            if not d_id:
                                # Create missing Analytic Account
                                logger.info(f"Creating missing Analytic Account: {s_name}")
                                try:
                                    # Need a plan. Find 'Default' or first plan.
                                    # Cache plans if not cached
                                    if not hasattr(fix_bill_analytics, 'default_plan_id'):
                                        plans = dest_models.execute_kw(dest_db, dest_uid, dest_pass, 'account.analytic.plan', 'search', [[]], {'limit': 1})
                                        if plans:
                                            fix_bill_analytics.default_plan_id = plans[0]
                                        else:
                                            # Create Default Plan
                                            fix_bill_analytics.default_plan_id = dest_models.execute_kw(dest_db, dest_uid, dest_pass, 'account.analytic.plan', 'create', [{'name': 'Default'}])
                                    
                                    new_aa_id = dest_models.execute_kw(dest_db, dest_uid, dest_pass, 'account.analytic.account', 'create', [{'name': s_name, 'plan_id': fix_bill_analytics.default_plan_id}])
                                    dest_map_name_to_id[s_name] = new_aa_id
                                    d_id = new_aa_id
                                    logger.info(f"Created {s_name} with ID {d_id}")
                                except Exception as e:
                                    logger.error(f"Failed to create account {s_name}: {e}")
                            
                            if d_id:
                                new_dist[str(d_id)] = percent
                    
                    if new_dist:
                        lines_to_update.append((1, d_line['id'], {'analytic_distribution': new_dist}))

            if lines_to_update:
                dest_models.execute_kw(dest_db, dest_uid, dest_pass, 'account.move', 'write', [[bill_id], {'invoice_line_ids': lines_to_update}])
                count_updated += 1
                if count_updated % 10 == 0:
                    logger.info(f"Updated {count_updated} bills...")

        except Exception as e:
            logger.error(f"Error processing bill {bill_id}: {e}")

    logger.info(f"Finished. Updated {count_updated} bills.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fix Analytic Distribution on Bills')
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    
    # Source args
    parser.add_argument('--src-url', required=True)
    parser.add_argument('--src-db', required=True)
    parser.add_argument('--src-user', required=True)
    parser.add_argument('--src-password', required=True)
    
    args = parser.parse_args()
    
    fix_bill_analytics(args.url, args.db, args.user, args.password, args.src_url, args.src_db, args.src_user, args.src_password)
