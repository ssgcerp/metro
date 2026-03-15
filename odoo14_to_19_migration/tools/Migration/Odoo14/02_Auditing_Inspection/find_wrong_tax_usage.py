
import xmlrpc.client
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def find_wrong_sales_taxes(url, db, user, password):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    logger.info("Scanning ALL companies for Sales Invoices using Purchase Taxes (2025-2026)...")
    
    companies = models.execute_kw(db, uid, password, 'res.company', 'search_read', [[]], {'fields': ['name']})
    
    total_wrong = 0
    
    for c in companies:
        cid = c['id']
        cname = c['name']
        
        # Find posted sales invoices
        domain = [
            ('company_id', '=', cid),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('date', '>=', '2025-01-01')
        ]
        
        # We want lines where tax_ids.type_tax_use = 'purchase'
        # searching this via ORM domain is tricky for many2many.
        # easier to finding purchase taxes first, then finding lines using them.
        
        purchase_tax_ids = models.execute_kw(db, uid, password, 'account.tax', 'search', 
            [[('company_id', '=', cid), ('type_tax_use', '=', 'purchase')]])
            
        if not purchase_tax_ids:
            continue
            
        # Inspect lines of sales invoices using these taxes
        # This search might be heavy, so let's filter by move domain
        moves = models.execute_kw(db, uid, password, 'account.move', 'search', [domain])
        
        if not moves:
            continue
            
        wrong_lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_count', [[
            ('move_id', 'in', moves),
            ('tax_ids', 'in', purchase_tax_ids)
        ]])
        
        if wrong_lines > 0:
            logger.warning(f"!!! Company {cname} has {wrong_lines} Sales Invoice lines using PURCHASE TAXES !!!")
            total_wrong += wrong_lines
            
            # Identify which taxes specifically
            lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read', 
                [[('move_id', 'in', moves), ('tax_ids', 'in', purchase_tax_ids)]],
                {'fields': ['tax_ids'], 'limit': 10}
            )
            sample_tax_ids = set()
            for l in lines:
                sample_tax_ids.update(l['tax_ids'])
                
            logger.info(f"    Sample Incorrect Tax IDs: {list(sample_tax_ids)}")
            
        else:
            logger.info(f"Company {cname}: Clean (No Purchase Taxes on Sales)")

    logger.info(f"Scan Complete. Total potentially wrong lines: {total_wrong}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    find_wrong_sales_taxes(args.url, args.db, args.user, args.password)
