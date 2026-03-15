
import xmlrpc.client
import argparse
import logging
from pprint import pprint

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def inspect_taxes(url, db, user, password):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    # 1. Get all companies
    companies = models.execute_kw(db, uid, password, 'res.company', 'search_read', [[]], {'fields': ['name']})
    
    for c in companies:
        cid = c['id']
        cname = c['name']
        logger.info(f"\n========================================")
        logger.info(f"Checking Company: {cname} (ID: {cid})")
        
        # 2. Search for Standard Output Tax (Sales) - assuming 'VAT 5%' or distinct names
        # We look for Sales taxes (type_tax_use='sale') usually populated in invoices
        tax_ids = models.execute_kw(db, uid, password, 'account.tax', 'search', [[('company_id', '=', cid), ('type_tax_use', '=', 'sale'), ('amount', '=', 5.0)]])
        
        if not tax_ids:
            logger.warning(f"  No 5% Sales Tax found for {cname}")
            continue
            
        taxes = models.execute_kw(db, uid, password, 'account.tax', 'read', [tax_ids], {'fields': ['name', 'invoice_repartition_line_ids']})
        
        for tax in taxes:
            logger.info(f"  Tax: {tax['name']} (ID: {tax['id']})")
            
            # 3. Check Repartition Lines (this defines which Account and TAGS are applied)
            repartition_ids = tax['invoice_repartition_line_ids']
            if not repartition_ids:
                logger.warning("    No repartition lines!")
                continue
                
            repartition_lines = models.execute_kw(db, uid, password, 'account.tax.repartition.line', 'read', [repartition_ids], {'fields': ['repartition_type', 'tag_ids', 'account_id']})
            
            for line in repartition_lines:
                # We care about lines that have tags (Tax Grids)
                if line['tag_ids']:
                    tags = models.execute_kw(db, uid, password, 'account.account.tag', 'read', [line['tag_ids']], {'fields': ['name']})
                    tag_names = [t['name'] for t in tags]
                    logger.info(f"    - Type: {line['repartition_type']} | Tags: {tag_names}")
                else:
                    pass
                    # logger.info(f"    - Type: {line['repartition_type']} | No Tags")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    inspect_taxes(args.url, args.db, args.user, args.password)
