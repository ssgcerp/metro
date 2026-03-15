
import xmlrpc.client
import argparse
import logging
from pprint import pprint

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def inspect_moves(url, db, user, password, company_name):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    # Get Company ID
    cids = models.execute_kw(db, uid, password, 'res.company', 'search', [[('name', 'ilike', company_name)]])
    if not cids:
        logger.error("Company not found")
        return
    cid = cids[0]
    
    logger.info(f"Inspecting moves for {company_name} (ID: {cid}) since 2026-01-01")
    
    domain = [
        ('company_id', '=', cid),
        ('state', '=', 'posted'),
        # ('move_type', 'in', ['out_invoice', 'out_refund']),
        ('date', '>=', '2026-01-01')
    ]
    move_ids = models.execute_kw(db, uid, password, 'account.move', 'search', [domain])
    logger.info(f"Found {len(move_ids)} moves.")
    
    if not move_ids:
        return

    # Inspect first 3 moves
    for mid in move_ids[:3]:
        move = models.execute_kw(db, uid, password, 'account.move', 'read', [mid], {'fields': ['name', 'line_ids']})[0]
        logger.info(f"Move: {move['name']}")
        
        lines = models.execute_kw(db, uid, password, 'account.move.line', 'read', [move['line_ids']], {'fields': ['name', 'tax_ids', 'tax_line_id', 'tax_tag_ids']})
        
        for l in lines:
            # Check if it has credit or debit to be useful
            if l['name'] or l['tax_ids']: 
                logger.info(f"  Line: {l['name']}")
                logger.info(f"    Tax IDs used: {l['tax_ids']}")
                logger.info(f"    Tax Line ID: {l['tax_line_id']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    parser.add_argument('--company', default='FUJAIRAH')
    args = parser.parse_args()
    
    inspect_moves(args.url, args.db, args.user, args.password, args.company)
