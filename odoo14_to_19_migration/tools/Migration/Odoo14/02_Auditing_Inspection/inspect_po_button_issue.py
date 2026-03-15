
import xmlrpc.client
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def inspect_po(url, db, user, password, po_name):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    ids = models.execute_kw(db, uid, password, 'purchase.order', 'search', [[('name', '=', po_name)]])
    if not ids:
        logger.error(f"PO {po_name} not found.")
        return

    fields = ['name', 'state', 'invoice_status', 'amount_total', 'partner_id']
    po = models.execute_kw(db, uid, password, 'purchase.order', 'read', [ids], {'fields': fields})[0]
    
    logger.info(f"PO: {po['name']}")
    logger.info(f"State: {po['state']}")
    logger.info(f"Invoice Status: {po['invoice_status']}") # to invoice, no, invoiced
    logger.info(f"Amount: {po['amount_total']}")
    
    # Check Order Lines to see quantities
    line_ids = models.execute_kw(db, uid, password, 'purchase.order.line', 'search', [[('order_id', '=', ids[0])]])
    lines = models.execute_kw(db, uid, password, 'purchase.order.line', 'read', [line_ids], {'fields': ['product_id', 'product_qty', 'qty_received', 'qty_invoiced']})
    
    logger.info("Lines:")
    for l in lines:
        logger.info(f" - Prod: {l['product_id'][1]} | Qty: {l['product_qty']} | Rec: {l['qty_received']} | Inv: {l['qty_invoiced']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    parser.add_argument('--po', default='P00004')
    args = parser.parse_args()
    
    inspect_po(args.url, args.db, args.user, args.password, args.po)
