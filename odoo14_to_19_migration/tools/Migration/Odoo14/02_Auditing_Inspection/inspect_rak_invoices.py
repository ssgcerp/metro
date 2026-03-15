
import xmlrpc.client
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def inspect_rak_inv(url, db, user, password):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    # RAK ID = 2
    cid = 2
    
    # Get recent Sales Invoices
    inv_ids = models.execute_kw(db, uid, password, 'account.move', 'search', 
        [[('company_id', '=', cid), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]],
        {'limit': 5, 'order': 'date desc'}
    )
    
    if not inv_ids:
        logger.warning("No RAK invoices found.")
        return

    logger.info(f"Inspecting {len(inv_ids)} RAK Invoices:")
    
    invoices = models.execute_kw(db, uid, password, 'account.move', 'read', [inv_ids], {'fields': ['name', 'date', 'invoice_line_ids']})
    
    for inv in invoices:
        logger.info(f"Invoice: {inv['name']} Date: {inv['date']}")
        lines = models.execute_kw(db, uid, password, 'account.move.line', 'read', [inv['invoice_line_ids']], {'fields': ['name', 'tax_ids']})
        for l in lines:
            if l['tax_ids']:
                # Get tax details
                taxes = models.execute_kw(db, uid, password, 'account.tax', 'read', [l['tax_ids']], {'fields': ['name', 'amount', 'type_tax_use', 'company_id']})
                tax_info = ", ".join([f"{t['name']} ({t['amount']}%) ID:{t['id']} Co:{t['company_id'][1]}" for t in taxes])
                logger.info(f"  - Line: {l['name']} | Tax: {tax_info}")
            else:
                logger.info(f"  - Line: {l['name']} | Tax: NONE")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    inspect_rak_inv(args.url, args.db, args.user, args.password)
