
import xmlrpc.client
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def inspect_tax_74(url, db, user, password):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    tax = models.execute_kw(db, uid, password, 'account.tax', 'read', [74], 
        {'fields': ['name', 'type_tax_use', 'amount', 'invoice_repartition_line_ids', 'refund_repartition_line_ids']}
    )[0]
    
    logger.info(f"Tax: {tax['name']} (ID: {tax['id']})")
    logger.info(f"Type: {tax['type_tax_use']}")
    
    # Check Repartitions
    rep_lines = models.execute_kw(db, uid, password, 'account.tax.repartition.line', 'read', [tax['invoice_repartition_line_ids']], 
        {'fields': ['repartition_type', 'tag_ids', 'account_id']})
    
    logger.info("Invoice Repartition Lines:")
    for l in rep_lines:
        logger.info(f"  - {l['repartition_type']} | Account: {l['account_id']} | Tags: {l['tag_ids']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    inspect_tax_74(args.url, args.db, args.user, args.password)
