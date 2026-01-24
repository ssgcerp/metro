
import xmlrpc.client
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def inspect_taxes(url, db, user, password):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    # 1. Inspect Companies for Default Taxes
    logging.info("--- COMPANIES & DEFAULT TAXES ---")
    companies = models.execute_kw(db, uid, password, 'res.company', 'search_read', [[]], {'fields': ['name', 'account_purchase_tax_id']})
    
    company_defaults = {}
    for c in companies:
        tax_info = c['account_purchase_tax_id']
        tax_name = tax_info[1] if tax_info else "None"
        tax_id = tax_info[0] if tax_info else False
        logging.info(f"Company: {c['name']} | Default Purchase Tax: {tax_name} (ID: {tax_id})")
        company_defaults[c['id']] = tax_id

    # 2. Find the "Wrong" Tax
    logging.info("\n--- SEARCHING FOR WRONG TAX '5% R C' ---")
    # Search for anything looking like 5% and R
    wrong_taxes = models.execute_kw(db, uid, password, 'account.tax', 'search_read', [[('name', 'ilike', '5%')]], {'fields': ['name', 'company_id']})
    
    target_wrong_ids = []
    
    for t in wrong_taxes:
        if "R C" in t['name'] or "Reverse" in t['name']:
             logging.info(f"Potential WRONG Tax Found: {t['name']} (ID: {t['id']}) | Company: {t['company_id'][1]}")
             target_wrong_ids.append(t['id'])
        else:
             logging.info(f"Other 5% Tax: {t['name']} (ID: {t['id']})")

    if not target_wrong_ids:
        logging.warning("No tax matching '5% R C' found. Please check exact name.")
        return

    # 3. Check Affected Vendor Bill Lines
    logging.info("\n--- AFFECTED VENDOR BILL LINES ---")
    # Search lines where tax_ids in target_wrong_ids
    # AND move type is in_invoice
    
    domain = [
        ('move_id.move_type', '=', 'in_invoice'),
        ('tax_ids', 'in', target_wrong_ids)
    ]
    
    line_count = models.execute_kw(db, uid, password, 'account.move.line', 'search_count', [domain])
    logging.info(f"Found {line_count} invoice lines using the wrong tax(es).")
    
    if line_count > 0:
        lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read', [domain], {'fields': ['name', 'move_id', 'tax_ids', 'company_id'], 'limit': 10})
        for l in lines:
            logging.info(f" - Bill: {l['move_id'][1]} | Line: {l['name']} | Taxes: {l['tax_ids']} | Comp: {l['company_id'][1]}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    inspect_taxes(args.url, args.db, args.user, args.password)
