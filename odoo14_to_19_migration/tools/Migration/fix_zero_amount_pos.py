
import xmlrpc.client
import logging
import argparse

# Odoo 19 Credentials (Target)
URL_19 = "https://metro.equdaierp.com"
DB_19 = "metrodb"
USER_19 = "admin"
PASS_19 = "Amaze@321"

# Odoo 14 Credentials (Source)
URL_14 = "https://erpmfs.com"
DB_14 = "metro_production_8_8_22"
USER_14 = "Sales.auh@metrofiresystems.com"
PASS_14 = "Sales@185734"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_zero_pos(dry_run=True):
    try:
        # Connect to Odoo 19
        common_19 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_19))
        uid_19 = common_19.authenticate(DB_19, USER_19, PASS_19, {})
        models_19 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_19))
        
        # Connect to Odoo 14
        common_14 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_14))
        uid_14 = common_14.authenticate(DB_14, USER_14, PASS_14, {})
        models_14 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_14))

        logger.info("Connected to both Odoo instances.")

        # 0. Fetch all Company IDs for Context
        companies = models_19.execute_kw(DB_19, uid_19, PASS_19, 'res.company', 'search_read', [[]], {'fields': ['id']})
        all_company_ids = [c['id'] for c in companies]
        CTX = {'allowed_company_ids': all_company_ids}
        logger.info(f"Using Context with Allowed Companies: {all_company_ids}")

        # 1. Search Odoo 19 for POs with amount_total = 0
        pos_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order', 'search_read', 
            [[('amount_total', '=', 0.0)]], 
            {'fields': ['name', 'state', 'order_line', 'company_id'], 'context': CTX})

        logger.info(f"Found {len(pos_19)} POs with 0 amount in Odoo 19.")
        
        # Cache for specific items if needed (e.g. taxes)
        # tax_map_19 = {name: id}
        # Pre-fetch taxes from 19 to help mapping
        all_taxes_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.tax', 'search_read', [[]], {'fields': ['name', 'company_id'], 'context': CTX})
        # Map: (Name, CompanyID) -> TaxID
        tax_map = {(t['name'], t['company_id'][0]): t['id'] for t in all_taxes_19}

        fixed_count = 0
        failed_count = 0

        for po in pos_19:
            po_name = po['name']
            po_state = po['state']
            po_id = po['id']
            company_id = po['company_id'][0]

            try:
                # 2. Find matching PO in Odoo 14
                po_14 = models_14.execute_kw(DB_14, uid_14, PASS_14, 'purchase.order', 'search_read', 
                    [[('name', '=', po_name)]], 
                    {'fields': ['order_line'], 'limit': 1})

                if not po_14:
                    logger.warning(f"PO {po_name} not found in Odoo 14. Skipping.")
                    continue

                line_ids_14 = po_14[0]['order_line']
                lines_14 = models_14.execute_kw(DB_14, uid_14, PASS_14, 'purchase.order.line', 'read', 
                    [line_ids_14], 
                    {'fields': ['name', 'price_unit', 'product_qty', 'taxes_id', 'product_id']}) # taxes_id returns ids

                # Need tax names from 14
                all_tax_ids_14 = []
                for l in lines_14:
                    all_tax_ids_14.extend(l['taxes_id'])
                
                tax_names_14 = {} # ID -> Name
                if all_tax_ids_14:
                    taxes_14_data = models_14.execute_kw(DB_14, uid_14, PASS_14, 'account.tax', 'read', 
                        [list(set(all_tax_ids_14))], {'fields': ['name']})
                    for t in taxes_14_data:
                        tax_names_14[t['id']] = t['name']

                # 3. Get Odoo 19 Lines
                line_ids_19 = po['order_line']
                # Check removed to allow restoration logic below

                # 3. Get Odoo 19 Lines
                line_ids_19 = po['order_line']
                lines_19 = []
                if line_ids_19:
                    lines_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order.line', 'read', 
                        [line_ids_19], 
                        {'fields': ['product_id', 'name', 'price_unit'], 'context': CTX}) 

                # Helper to find product
                def find_product(p_name_14):
                    # 1. Try Exact Match
                    prod = models_19.execute_kw(DB_19, uid_19, PASS_19, 'product.product', 'search_read',
                        [[('name', '=', p_name_14)]], {'fields': ['id'], 'limit': 1})
                    if prod: return prod[0]['id']

                    # 2. Try Default Code Extraction [CODE] Name
                    import re
                    match = re.match(r'^\[(.*?)\]\s*(.*)', p_name_14)
                    if match:
                        code = match.group(1)
                        name_part = match.group(2)
                        
                        # Search by Code
                        prod = models_19.execute_kw(DB_19, uid_19, PASS_19, 'product.product', 'search_read',
                            [[('default_code', '=', code)]], {'fields': ['id'], 'limit': 1})
                        if prod: return prod[0]['id']
                        
                        # Search by Name Part
                        # prod = models_19.execute_kw(DB_19, uid_19, PASS_19, 'product.product', 'search_read',
                        #     [[('name', '=', name_part)]], {'fields': ['id'], 'limit': 1})
                        # if prod: return prod[0]['id']
                    
                    return False

                # CASE 1: No Lines in 19, but Lines in 14 -> Restore Lines
                if not lines_19 and lines_14:
                    logger.info(f"Restoring {len(lines_14)} lines for PO {po_name}...")
                    
                    if not dry_run:
                        if po_state in ['purchase', 'done']:
                            models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order', 'button_draft', [[po_id]], {'context': CTX})

                    for l_14 in lines_14:
                        product_name_14 = l_14['product_id'][1] if l_14['product_id'] else l_14['name']
                        
                        product_id_19 = find_product(product_name_14)
                        
                        if not product_id_19:
                            # Try finding by Line Name/Description if different
                            if l_14['name'] != product_name_14:
                                 product_id_19 = find_product(l_14['name'])
                        
                        if not product_id_19:
                            logger.warning(f"  Product '{product_name_14}' not found in 19. Skipping line.")
                            continue
                            
                        vals = {
                            'order_id': po_id,
                            'name': l_14['name'],
                            'product_id': product_id_19,
                            'product_qty': l_14['product_qty'],
                            'price_unit': l_14['price_unit'],
                        }
                        
                        if not dry_run:
                            models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order.line', 'create', [vals], {'context': CTX})

                    if not dry_run:
                         # Restore State
                         if po_state in ['purchase', 'done']:
                             models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order', 'button_confirm', [[po_id]], {'context': CTX})
                         if po_state == 'done':
                             try:
                                 models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order', 'button_done', [[po_id]], {'context': CTX})
                             except:
                                 pass
                    
                    fixed_count += 1
                    continue

                # CASE 2: Line Count Mismatch -> Delete Odoo 19 Lines & Restore from 14
                if len(lines_19) != len(lines_14):
                    logger.info(f"PO {po_name}: Line count mismatch (14: {len(lines_14)}, 19: {len(lines_19)}). Overwriting lines.")
                    
                    if not dry_run:
                        if po_state in ['purchase', 'done']:
                            models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order', 'button_draft', [[po_id]], {'context': CTX})
                        
                        # Delete existing lines
                        to_unlink = [l['id'] for l in lines_19]
                        if to_unlink:
                            models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order.line', 'unlink', [to_unlink], {'context': CTX})
                            
                    # Reset lines_19 to empty so it falls into restoration logic (or duplicate restoration logic here)
                    # We can just empty lines_19 and verify lines_14 exists, then call a shared helper? 
                    # Code duplication is safer for quick edit.
                    
                    # Logically, if we delete lines, we are in "No Lines in 19" state.
                    # We can just leverage the implementation of CASE 1 if we construct it right?
                    # But CASE 1 is above.
                    
                    # Let's Implement Restoration Here directly
                    for l_14 in lines_14:
                        product_name_14 = l_14['product_id'][1] if l_14['product_id'] else l_14['name']
                        
                        product_id_19 = find_product(product_name_14)
                        
                        if not product_id_19:
                            if l_14['name'] != product_name_14:
                                 product_id_19 = find_product(l_14['name'])
                        
                        if not product_id_19:
                            logger.warning(f"  Product '{product_name_14}' not found in 19. Skipping line.")
                            continue
                            
                        vals = {
                            'order_id': po_id,
                            'name': l_14['name'],
                            'product_id': product_id_19,
                            'product_qty': l_14['product_qty'],
                            'price_unit': l_14['price_unit'],
                        }
                        
                        if not dry_run:
                            models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order.line', 'create', [vals], {'context': CTX})

                    if not dry_run:
                         if po_state in ['purchase', 'done']:
                             models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order', 'button_confirm', [[po_id]], {'context': CTX})
                         if po_state == 'done':
                             try:
                                 models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order', 'button_done', [[po_id]], {'context': CTX})
                             except:
                                 pass
                    
                    fixed_count += 1
                    continue

                # CASE 3: Lines Exist -> Update Prices (Existing Logic)
                # Prepare updates
                updates_needed = False
                
                logger.info(f"Processing PO {po_name} (State: {po_state})...")
                
                if not dry_run:
                    if po_state in ['purchase', 'done']:
                        models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order', 'button_draft', [[po_id]], {'context': CTX})
                
                for i in range(len(lines_19)):
                    l_19 = lines_19[i]
                    l_14 = lines_14[i]
                    
                    price_14 = l_14['price_unit']
                    # tax_ids_14 = l_14['taxes_id']
                    
                    if not dry_run:
                        # Update Line - PRICE ONLY (User requested to keep taxes as is)
                        vals = {'price_unit': price_14}
                        
                        # Only update if price is different (optimization)
                        if l_19.get('price_unit') != price_14:
                             models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order.line', 'write', [[l_19['id']], vals], {'context': CTX})
                             updates_needed = True
                        
                if not dry_run:
                     # Restore State
                     if po_state in ['purchase', 'done']:
                         models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order', 'button_confirm', [[po_id]], {'context': CTX})
                     if po_state == 'done':
                         try:
                             models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order', 'button_done', [[po_id]], {'context': CTX})
                         except:
                             pass # Button done might strict strict check
                
                fixed_count += 1

            except Exception as inner_e:
                logger.error(f"Error processing PO {po_name}: {str(inner_e)}")
                failed_count += 1

        logger.info(f"\n--- Summary ---")
        logger.info(f"Fixed: {fixed_count}")
        logger.info(f"Failed: {failed_count}")
        if dry_run:
            logger.info("NOTE: Dry Run Mode - No changes made.")

    except Exception as e:
        logger.error(f"Global Error: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true', help='Execute updates (disable dry run)')
    args = parser.parse_args()
    
    print(f"Arguments: {args}")
    fix_zero_pos(dry_run=not args.run)
