import xmlrpc.client
import logging
import argparse

# Odoo 19 Credentials (Target)
URL_19 = "https://metro.equdaierp.com"
DB_19 = "newdb"
USER_19 = "admin"
PASS_19 = "Amaze@321"

# Odoo 18 Credentials (Source)
URL_18 = "https://metro-fire-system-llc.odoo.com"
DB_18 = "metro-fire-system-llc"
USER_18 = "sruthi@metrofiresystems.com"
PASS_18 = "Sruthi@321"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_zero_invoices(dry_run=True):
    try:
        # Connect to Odoo 19
        common_19 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_19), allow_none=True)
        uid_19 = common_19.authenticate(DB_19, USER_19, PASS_19, {})
        models_19 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_19), allow_none=True)
        
        # Connect to Odoo 18
        common_18 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_18), allow_none=True)
        uid_18 = common_18.authenticate(DB_18, USER_18, PASS_18, {})
        models_18 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_18), allow_none=True)

        logger.info("Connected to both Odoo instances.")

        # 1. Search Odoo 19 for Customer Invoices with amount_total = 0
        invs_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'search_read', 
            [[('move_type', '=', 'out_invoice'), ('amount_total', '=', 0.0)]], 
            {'fields': ['name', 'state', 'invoice_line_ids', 'company_id'], 'limit': 5000})

        logger.info(f"Found {len(invs_19)} Customer Invoices with 0 amount in Odoo 19.")
        
        fixed_count = 0
        failed_count = 0
        
        # Helper to find product in Odoo 19
        def find_product(p_name_18):
            if not p_name_18: return False
            prod = models_19.execute_kw(DB_19, uid_19, PASS_19, 'product.product', 'search_read',
                [[('name', '=', p_name_18)]], {'fields': ['id'], 'limit': 1})
            if prod: return prod[0]['id']

            import re
            match = re.match(r'^\[(.*?)\]\s*(.*)', p_name_18)
            if match:
                code = match.group(1)
                prod = models_19.execute_kw(DB_19, uid_19, PASS_19, 'product.product', 'search_read',
                    [[('default_code', '=', code)]], {'fields': ['id'], 'limit': 1})
                if prod: return prod[0]['id']
            return False

        for inv in invs_19:
            inv_name = inv['name']
            inv_state = inv['state']
            inv_id = inv['id']
            # if name is false, it's a completely blank draft
            if not inv_name:
                logger.warning(f"Found blank draft invoice (ID: {inv_id}). Skipping.")
                continue

            try:
                # 2. Find matching Invoice in Odoo 18
                inv_18 = models_18.execute_kw(DB_18, uid_18, PASS_18, 'account.move', 'search_read', 
                    [[('name', '=', inv_name), ('move_type', '=', 'out_invoice')]], 
                    {'fields': ['invoice_line_ids'], 'limit': 1})

                if not inv_18:
                    logger.warning(f"Invoice {inv_name} not found in Odoo 18. Skipping.")
                    continue

                line_ids_18 = inv_18[0]['invoice_line_ids']
                if not line_ids_18:
                    logger.warning(f"Invoice {inv_name} has NO lines in Odoo 18. Skipping.")
                    continue

                lines_18 = models_18.execute_kw(DB_18, uid_18, PASS_18, 'account.move.line', 'read', 
                    [line_ids_18], 
                    {'fields': ['name', 'price_unit', 'quantity', 'tax_ids', 'product_id', 'display_type']})

                # Only process product lines
                lines_18 = [l for l in lines_18 if l.get('display_type') == 'product' or not l.get('display_type')]

                line_ids_19 = inv['invoice_line_ids']
                
                # Check if Odoo 19 has lines. If so, and we just need to update prices, let's do that.
                # If Odoo 19 is missing lines entirely, or has wrong count, we'll wipe and recreate.
                
                # For safety on account.move, we only write if it's draft.
                if not dry_run and inv_state != 'draft':
                    # To add lines, it must be in draft
                    models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'button_draft', [[inv_id]])
                    inv_state = 'draft'
                
                if len(line_ids_19) != len(lines_18):
                    logger.info(f"Restoring {len(lines_18)} missing/mismatched lines for {inv_name}...")
                    
                    if not dry_run:
                        if line_ids_19:
                            models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move.line', 'unlink', [line_ids_19])
                        
                        for l_18 in lines_18:
                            product_name_18 = l_18['product_id'][1] if l_18['product_id'] else l_18['name']
                            
                            product_id_19 = find_product(product_name_18)
                            if not product_id_19 and l_18['name'] != product_name_18:
                                 product_id_19 = find_product(l_18['name'])
                            
                            vals = {
                                'move_id': inv_id,
                                'name': l_18['name'] or 'Product',
                                'quantity': l_18['quantity'],
                                'price_unit': l_18['price_unit'],
                            }
                            if product_id_19:
                                vals['product_id'] = product_id_19
                                
                            models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move.line', 'create', [vals])
                else:
                    logger.info(f"Checking {len(lines_18)} existing lines for {inv_name} prices...")
                    
                    lines_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move.line', 'read', 
                        [line_ids_19], {'fields': ['id', 'price_unit', 'display_type']})
                    lines_19 = [l for l in lines_19 if l.get('display_type') == 'product' or not l.get('display_type')]
                    
                    for i in range(min(len(lines_19), len(lines_18))):
                        l_19 = lines_19[i]
                        l_18 = lines_18[i]
                        
                        if l_19['price_unit'] != l_18['price_unit']:
                            if not dry_run:
                                models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move.line', 'write', [[l_19['id']], {'price_unit': l_18['price_unit']}])

                if not dry_run:
                    # In Odoo, creating move.lines doesn't instantly recompute totals sometimes,
                    # so we leave them in draft, or we could post them. Let's leave in draft for user verify.
                    pass 
                
                fixed_count += 1

            except Exception as inner_e:
                logger.error(f"Error processing invoice {inv_name}: {str(inner_e)}")
                failed_count += 1

        logger.info(f"\n--- Summary ---")
        logger.info(f"Fixed/Checked: {fixed_count}")
        logger.info(f"Failed: {failed_count}")
        if dry_run:
            logger.info("NOTE: Dry Run Mode - No changes made.")

    except Exception as e:
        logger.error(f"Global Error: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true', help='Execute updates (disable dry run)')
    args = parser.parse_args()
    
    fix_zero_invoices(dry_run=not args.run)
