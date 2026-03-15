
import xmlrpc.client
import argparse
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
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

def inspect_explicit(url, db, user, password):
    logger.info(f"Connecting to Source {url}...")
    uid, models = connect_to_odoo(url, db, user, password)
    if not uid:
        logger.error("Authentication Failed")
        return

    # 1. Check Companies
    companies = models.execute_kw(db, uid, password, 'res.company', 'search_read', [[]], {'fields': ['name']})
    logger.info(f"Found {len(companies)} companies:")
    for c in companies:
        logger.info(f" - [{c['id']}] {c['name']}")

    # 2. Check Specific Bill "Roopesh"
    target_ref = "Roopesh"
    logger.info(f"\nSearching for Bill with Ref ilike '{target_ref}'...")
    domain = [('ref', 'ilike', target_ref), ('move_type', '=', 'in_invoice')]
    bill_ids = models.execute_kw(db, uid, password, 'account.move', 'search', [domain], {'limit': 5})
    
    if bill_ids:
        bills = models.execute_kw(db, uid, password, 'account.move', 'read', [bill_ids], {'fields': ['name', 'ref', 'invoice_line_ids', 'company_id']})
        for b in bills:
            logger.info(f"FOUND BILL: {b['name']} | Ref: {b['ref']} | Comp: {b['company_id']}")
            # Check lines for analytic_distribution
            lines = models.execute_kw(db, uid, password, 'account.move.line', 'read', [b['invoice_line_ids']], {'fields': ['name', 'analytic_distribution']})
            for l in lines:
                logger.info(f"   Line: {l['name'][:40]}... | Dist: {l.get('analytic_distribution')}")
    else:
        logger.info("Bill NOT FOUND.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--db', required=True)
    parser.add_argument('--user', required=True)
    parser.add_argument('--password', required=True)
    args = parser.parse_args()
    
    inspect_explicit(args.url, args.db, args.user, args.password)
