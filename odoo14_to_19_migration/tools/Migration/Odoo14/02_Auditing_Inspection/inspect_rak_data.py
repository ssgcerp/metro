
import xmlrpc.client
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def inspect_rak(url, db, user, password):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    # 1. Search for companies likely to be RAK
    companies = models.execute_kw(db, uid, password, 'res.company', 'search_read', 
        [['|', ('name', 'ilike', 'Ras'), ('name', 'ilike', 'RAK')]], 
        {'fields': ['name', 'id']}
    )
    
    if not companies:
        logger.error("No company found matching 'Ras' or 'RAK'")
        return

    for c in companies:
        logger.info(f"\n--- Company: {c['name']} (ID: {c['id']}) ---")
        
        # 2. Count Posted Moves (Any Type)
        # Check all time first to see if it's dead
        count_all = models.execute_kw(db, uid, password, 'account.move', 'search_count', 
            [[('company_id', '=', c['id']), ('state', '=', 'posted')]])
        logger.info(f"  Total Posted Moves (All Time): {count_all}")
        
        # Check 2025+
        count_2025 = models.execute_kw(db, uid, password, 'account.move', 'search_count', 
            [[('company_id', '=', c['id']), ('state', '=', 'posted'), ('date', '>=', '2025-01-01')]])
        logger.info(f"  Total Posted Moves (Since Jan 2025): {count_2025}")
        
        if count_2025 > 0:
            # 3. Check for Sales (out_invoice, out_refund) specifically
            sales_count = models.execute_kw(db, uid, password, 'account.move', 'search_count', 
                [[('company_id', '=', c['id']), ('state', '=', 'posted'), 
                  ('date', '>=', '2025-01-01'), ('move_type', 'in', ['out_invoice', 'out_refund'])]])
            logger.info(f"  Sales Invoices (since Jan 2025): {sales_count}")
            
            # 4. Check POS entries (type='entry' and name like POS?)
            # Or just check entries with 5% tax
            # Search for moves using a 5% tax
            moves_with_tax = models.execute_kw(db, uid, password, 'account.move.line', 'search_count', 
                [[('company_id', '=', c['id']), ('parent_state', '=', 'posted'),
                  ('date', '>=', '2025-01-01'), ('tax_ids.amount', '=', 5.0), ('tax_ids.type_tax_use', '=', 'sale')]])
            logger.info(f"  Lines with 5% Sales Tax: {moves_with_tax}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    inspect_rak(args.url, args.db, args.user, args.password)
