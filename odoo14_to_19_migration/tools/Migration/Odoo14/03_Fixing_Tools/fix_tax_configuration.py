
import xmlrpc.client
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def fix_taxes(url, db, user, password):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    # Mapping: Company Name part -> Base Tag Name, Tax Tag Name
    mapping = {
        'DUBAI': ('1(b)B', '1(b)T'),
        'SHARJAH': ('1(c)B', '1(c)T'),
        'AJMAN': ('1(d)B', '1(d)T'),
        'RAS AL KHAIMAH': ('1(f)B', '1(f)T'),
        'FUJAIRAH': ('1(g)B', '1(g)T'),
        'ABU DHABI': ('1(a)B', '1(a)T'), # Verification
        # Excluding unknown ones for now to avoid wrong assignment
    }
    
    # 1. Fetch Tag IDs
    tag_map = {}
    tags = models.execute_kw(db, uid, password, 'account.account.tag', 'search_read', [[]], {'fields': ['name']})
    for t in tags:
        tag_map[t['name']] = t['id']
        
    # 2. Iterate Companies
    companies = models.execute_kw(db, uid, password, 'res.company', 'search_read', [[]], {'fields': ['name']})
    
    for c in companies:
        cname = c['name']
        cid = c['id']
        
        target_tags = None
        # Simple string matching
        for k, v in mapping.items():
            if k in cname.upper():
                target_tags = v
                break
        
        if not target_tags:
            logger.warning(f"Skipping Company {cname}: No mapping found.")
            continue
            
        base_tag_name, tax_tag_name = target_tags
        base_tag_id = tag_map.get(base_tag_name)
        tax_tag_id = tag_map.get(tax_tag_name)
        
        if not base_tag_id or not tax_tag_id:
            logger.error(f"Tags not found for {cname}: {base_tag_name}, {tax_tag_name}")
            continue
            
        logger.info(f"Processing {cname} -> Tags: {base_tag_name} ({base_tag_id}), {tax_tag_name} ({tax_tag_id})")
        
        # 3. Find 5% Sales Tax
        # Broad search: 5% positive amount, sales type.
        tax_ids = models.execute_kw(db, uid, password, 'account.tax', 'search', [[('company_id', '=', cid), ('type_tax_use', '=', 'sale'), ('amount', '=', 5.0)]])
        
        if not tax_ids:
            logger.warning(f"  No 5% Sales Tax found for {cname}")
            continue
            
        # Read tax to get repartition lines
        tax = models.execute_kw(db, uid, password, 'account.tax', 'read', [tax_ids[0]], {'fields': ['name', 'invoice_repartition_line_ids']})[0]
        logger.info(f"  Updating Tax: {tax['name']}")
        
        repartition_ids = tax['invoice_repartition_line_ids']
        repartition_lines = models.execute_kw(db, uid, password, 'account.tax.repartition.line', 'read', [repartition_ids], {'fields': ['repartition_type', 'tag_ids', 'account_id']})
        
        for line in repartition_lines:
            lid = line['id']
            # Update Base Line
            if line['repartition_type'] == 'base':
                # Only update if missing (or we can force update)
                # Let's force update to ensure correctness
                models.execute_kw(db, uid, password, 'account.tax.repartition.line', 'write', [[lid], {'tag_ids': [(6, 0, [base_tag_id])]}])
                logger.info(f"    - Updated BASE line {lid} with tag {base_tag_name}")
                
            # Update Tax Line (usually checks account_id presence too, but checking type is safer for simplified structure)
            elif line['repartition_type'] == 'tax':
                # Usually we want the tax line that posts to an account (not the potentially empty one if exists, though standard structure has 1 tax line)
                if line['account_id']: 
                    models.execute_kw(db, uid, password, 'account.tax.repartition.line', 'write', [[lid], {'tag_ids': [(6, 0, [tax_tag_id])]}])
                    logger.info(f"    - Updated TAX line {lid} with tag {tax_tag_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    fix_taxes(args.url, args.db, args.user, args.password)
