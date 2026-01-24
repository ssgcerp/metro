
import xmlrpc.client
import argparse
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[
    logging.FileHandler("debug_fix.log", mode='w'),
    logging.StreamHandler()
])
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

def test_fix_single(dest_url, dest_db, dest_user, dest_pass, src_url, src_db, src_user, src_pass):
    logger.info("Connecting...")
    d_uid, d_models = connect_to_odoo(dest_url, dest_db, dest_user, dest_pass)
    s_uid, s_models = connect_to_odoo(src_url, src_db, src_user, src_pass)

    # 1. Cache Maps
    aa_ids = d_models.execute_kw(dest_db, d_uid, dest_pass, 'account.analytic.account', 'search', [[]])
    aa_data = d_models.execute_kw(dest_db, d_uid, dest_pass, 'account.analytic.account', 'read', [aa_ids], {'fields': ['name']})
    dest_map = {rec['name']: rec['id'] for rec in aa_data}
    
    s_aa_ids = s_models.execute_kw(src_db, s_uid, src_pass, 'account.analytic.account', 'search', [[]])
    s_aa_data = s_models.execute_kw(src_db, s_uid, src_pass, 'account.analytic.account', 'read', [s_aa_ids], {'fields': ['name']})
    src_map = {str(rec['id']): rec['name'] for rec in s_aa_data}

    # 2. Find Bill
    target_ref = "Roopesh" # from previous test
    logger.info(f"Targeting Ref: {target_ref}")
    
    d_bills = d_models.execute_kw(dest_db, d_uid, dest_pass, 'account.move', 'search_read', [[('ref', 'ilike', target_ref), ('move_type', '=', 'in_invoice')]], {'fields': ['name', 'ref', 'invoice_line_ids']})
    
    if not d_bills:
        logger.error("Bill not found in Dest!")
        return
        
    for bill in d_bills:
        logger.info(f"\nProcessing Dest Bill: {bill['name']} | Ref: {bill['ref']}")
        
        # 3. Find Source
        src_bills = s_models.execute_kw(src_db, s_uid, src_pass, 'account.move', 'search_read', [[('name', '=', bill['name']), ('move_type', '=', 'in_invoice')]], {'fields': ['id', 'invoice_line_ids']})
        
        if not src_bills:
            logger.warning(" - Source Bill NOT FOUND by Name.")
            continue
            
        src_bill = src_bills[0]
        logger.info(f" - Found Source Bill ID: {src_bill['id']}")
        
        # 4. Lines
        # Dest Lines
        d_lines = d_models.execute_kw(dest_db, d_uid, dest_pass, 'account.move.line', 'read', [bill['invoice_line_ids']], {'fields': ['name', 'analytic_distribution']})
        
        # Source Lines (via header)
        s_line_ids = src_bill['invoice_line_ids']
        s_lines = s_models.execute_kw(src_db, s_uid, src_pass, 'account.move.line', 'read', [s_line_ids], {'fields': ['name', 'analytic_distribution']})
        
        logger.info(f" - Line Counts: Dest={len(d_lines)}, Src={len(s_lines)}")
        
        if len(d_lines) != len(s_lines):
             logger.warning("   MISMATCH COUNT")
             # Proceed anyway for debug
        
        for i in range(min(len(d_lines), len(s_lines))):
            dl = d_lines[i]
            sl = s_lines[i]
            logger.info(f"   Line {i}: Dest='{dl['name'][:20]}' | Src='{sl['name'][:20]}'")
            
            dist = sl.get('analytic_distribution')
            logger.info(f"     Source Dist: {dist}")
            
            if dist:
                new_dist = {}
                for sid, pct in dist.items():
                    sname = src_map.get(sid)
                    logger.info(f"       SID {sid} -> Name {sname}")
                    if sname:
                         did = dest_map.get(sname)
                         logger.info(f"       Name {sname} -> DestID {did}")
                         if did:
                             new_dist[str(did)] = pct
                
                logger.info(f"     Calculated Dest Dist: {new_dist}")
                if new_dist:
                    logger.info("     ** WOULD UPDATE **")
                else:
                    logger.info("     ** NO UPDATE (Mapping Failed?) **")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
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
    
    test_fix_single(args.url, args.db, args.user, args.password, args.src_url, args.src_db, args.src_user, args.src_password)
