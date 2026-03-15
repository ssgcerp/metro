
import xmlrpc.client
import argparse
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def fix_moves(url, db, user, password):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    # Mapping: Company Name -> Tags
    mapping = {
        'DUBAI': ('1(b)B', '1(b)T'),
        'SHARJAH': ('1(c)B', '1(c)T'),
        'AJMAN': ('1(d)B', '1(d)T'),
        'RAS AL KHAIMAH': ('1(f)B', '1(f)T'),
        'FUJAIRAH': ('1(g)B', '1(g)T'),
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
        for k, v in mapping.items():
            if k in cname.upper():
                target_tags = v
                break
        
        if not target_tags:
            continue
            
        base_tag_name, tax_tag_name = target_tags
        base_tag_id = tag_map.get(base_tag_name)
        tax_tag_id = tag_map.get(tax_tag_name)
        
        if not base_tag_id or not tax_tag_id:
            logger.error(f"Tags not found for {cname}")
            continue
            
        logger.info(f"Scanning Company: {cname} (Tags: {base_tag_id}, {tax_tag_id})")
        
        # 3. Find Relevant Moves (Posted Invoices/Refunds/Entries)
        # We target Jan 2026 mainly. POS entries are type='entry'
        domain = [
            ('company_id', '=', cid),
            ('state', '=', 'posted'),
            # ('move_type', 'in', ['out_invoice', 'out_refund']), # REMOVED to include POS
            ('date', '>=', '2025-01-01') 
        ]
        move_ids = models.execute_kw(db, uid, password, 'account.move', 'search', [domain])
        logger.info(f"  Found {len(move_ids)} posted moves (any type) since Jan 1, 2025.")
        
        if not move_ids:
            continue
            
        logger.info(f"  Analysing tax usage in {len(move_ids)} moves...")

        # Dynamic Tax Discovery
        # Search for lines in these moves that use ANY tax
        # optimization: search lines directly
        
        # We need to find which taxes are actually used in these moves that match our criteria (5% Sales)
        # 1. Get all unique taxes referenced in tax_ids or tax_line_id
        
        # This is hard to do efficiently via search without iterating. 
        # But we can search for ALL 5% sale taxes for the company, hoping the used ones are among them
        # (My previous attempt did this, but maybe strict amount=5.0 failed? or type?)
        # Let's broaden search: Name like 'VAT' or '5%'?
        
        candidates = models.execute_kw(db, uid, password, 'account.tax', 'search_read', 
            [[('company_id', '=', cid), ('type_tax_use', '=', 'sale')]], 
            {'fields': ['name', 'amount']}
        )
        
        # Filter in python for 5% (handling generic rounding or float issues)
        valid_tax_ids = []
        for t in candidates:
            if abs(t['amount'] - 5.0) < 0.1:
                valid_tax_ids.append(t['id'])
                
        if not valid_tax_ids:
            logger.warning("  No 5% Sales Taxes found at all.")
            continue
            
        logger.info(f"  Identified {len(valid_tax_ids)} valid 5% taxes: {valid_tax_ids}")
        
        # 5. Process in batches
        batch_size = 50
        updated_base = 0
        updated_tax = 0
        
        for i in range(0, len(move_ids), batch_size):
            batch = move_ids[i:i+batch_size]
            
            # Fetch Lines
            
            # A. Base Lines
            base_line_ids = models.execute_kw(db, uid, password, 'account.move.line', 'search', [[
                ('move_id', 'in', batch),
                ('tax_ids', 'in', valid_tax_ids)  # Match ANY valid 5% tax
            ]])
            
            if base_line_ids:
                models.execute_kw(db, uid, password, 'account.move.line', 'write', [base_line_ids, {'tax_tag_ids': [(4, base_tag_id)]}])
                updated_base += len(base_line_ids)
                
            # B. Tax Lines
            tax_line_ids = models.execute_kw(db, uid, password, 'account.move.line', 'search', [[
                ('move_id', 'in', batch),
                ('tax_line_id', 'in', valid_tax_ids) # Match ANY valid 5% tax
            ]])
            
            if tax_line_ids:
                models.execute_kw(db, uid, password, 'account.move.line', 'write', [tax_line_ids, {'tax_tag_ids': [(4, tax_tag_id)]}])
                updated_tax += len(tax_line_ids)
                
        logger.info(f"  Updated: {updated_base} Base Lines, {updated_tax} Tax Lines.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    fix_moves(args.url, args.db, args.user, args.password)
