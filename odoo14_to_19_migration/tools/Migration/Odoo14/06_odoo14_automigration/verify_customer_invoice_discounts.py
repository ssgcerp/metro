import xmlrpc.client
import ssl
import pandas as pd
import argparse
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

# Odoo 14 Credentials (Source)
URL_14 = "https://erpmfs.com"
DB_14 = "metro_production_8_8_22"
USER_14 = "Sales.auh@metrofiresystems.com"
PASS_14 = "Sales@185734"

# Odoo 19 Credentials (Target)
URL_19 = "https://metro.equdaierp.com"
DB_19 = "newdb"
USER_19 = "admin"
PASS_19 = "Amaze@321"

def get_odoo_client(url, db, username, password):
    ctx = ssl._create_unverified_context()
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ctx, allow_none=True)
    uid = common.authenticate(db, username, password, {})
    if not uid:
        raise Exception(f"Failed to authenticate to {url}")
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ctx, allow_none=True)
    return uid, models

def main():
    parser = argparse.ArgumentParser(description='Verify and Fix Customer Invoice Discounts (Odoo 14 -> Odoo 19)')
    parser.add_argument('--limit', type=int, default=100, help='Batch size for testing per company')
    parser.add_argument('--company-name', type=str, required=False, help='Company name in Odoo 19. If omitted, runs for all companies.')
    parser.add_argument('--fix', action='store_true', help='Actually apply fixes to Odoo 19')
    args = parser.parse_args()

    _logger.info("Connecting to Odoo instances...")
    uid_14, models_14 = get_odoo_client(URL_14, DB_14, USER_14, PASS_14)
    uid_19, models_19 = get_odoo_client(URL_19, DB_19, USER_19, PASS_19)

    # 1. Get Companies in Odoo 19
    if args.company_name:
        companies = models_19.execute_kw(DB_19, uid_19, PASS_19, 'res.company', 'search_read', [[('name', '=', args.company_name)]], {'fields': ['id', 'name']})
        if not companies:
            _logger.error(f"Company {args.company_name} not found in Odoo 19")
            return
    else:
        companies = models_19.execute_kw(DB_19, uid_19, PASS_19, 'res.company', 'search_read', [[]], {'fields': ['id', 'name']})
        _logger.info(f"Found {len(companies)} companies. Running for all companies.")

    all_results = []

    for company in companies:
        company_id_19 = company['id']
        company_name = company['name']
        
        _logger.info(f"--- Processing Company: {company_name} ---")

        # 2. Search for out_invoices in Odoo 19 for this company
        domain_19 = [('move_type', '=', 'out_invoice'), ('state', 'in', ['posted', 'draft']), ('company_id', '=', company_id_19)]
        invs_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'search_read', [domain_19], 
                                      {'fields': ['name', 'amount_total', 'invoice_line_ids', 'state'], 'limit': args.limit, 'order': 'id desc'})
        
        _logger.info(f"Found {len(invs_19)} invoices to verify in Odoo 19 (Company: {company_name})")

        for inv_19 in invs_19:
            inv_name = inv_19['name']
            if not inv_name or inv_name == '/':
                continue
                
            # 3. Find matching invoice in Odoo 14
            domain_14 = [('move_type', '=', 'out_invoice'), ('name', '=', inv_name)]
            invs_14 = models_14.execute_kw(DB_14, uid_14, PASS_14, 'account.move', 'search_read', [domain_14], 
                                          {'fields': ['name', 'amount_total', 'invoice_line_ids']})
            
            if not invs_14:
                continue
                
            inv_14 = invs_14[0]
            inv14_total = inv_14['amount_total']
            inv19_total_before = inv_19['amount_total']
            
            # Get lines detailed info
            lines_14 = models_14.execute_kw(DB_14, uid_14, PASS_14, 'account.move.line', 'search_read', 
                                           [[('id', 'in', inv_14['invoice_line_ids'])]], 
                                           {'fields': ['product_id', 'name', 'discount', 'price_unit', 'quantity', 'display_type']})
                                           
            lines_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move.line', 'search_read', 
                                           [[('id', 'in', inv_19['invoice_line_ids'])]], 
                                           {'fields': ['product_id', 'name', 'discount', 'price_unit', 'quantity', 'display_type']})
            
            # Calculate discounts for reporting
            o14_discount_amount = 0.0
            o14_discount_pcts = []
            for l in lines_14:
                if not l.get('display_type') and l.get('discount'):
                    disc = l['discount']
                    qty = l.get('quantity', 0.0)
                    price = l.get('price_unit', 0.0)
                    amount = qty * price * (disc / 100.0)
                    o14_discount_amount += amount
                    o14_discount_pcts.append(f"{disc}%")
                    
            o19_discount_amount = 0.0
            o19_discount_pcts = []
            for l in lines_19:
                if not l.get('display_type') and l.get('discount'):
                    disc = l['discount']
                    qty = l.get('quantity', 0.0)
                    price = l.get('price_unit', 0.0)
                    amount = qty * price * (disc / 100.0)
                    o19_discount_amount += amount
                    o19_discount_pcts.append(f"{disc}%")
                    
            # Also check global discounts if 'amount_discount' exists
            o14_global_discount = 0.0
            try:
                invs_14_global = models_14.execute_kw(DB_14, uid_14, PASS_14, 'account.move', 'search_read', [('id', '=', inv_14['id'])], {'fields': ['amount_discount']})
                if invs_14_global and 'amount_discount' in invs_14_global[0]:
                    o14_global_discount = invs_14_global[0]['amount_discount'] or 0.0
            except Exception:
                pass

            o19_global_discount = 0.0
            try:
                invs_19_global = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'search_read', [('id', '=', inv_19['id'])], {'fields': ['amount_discount']})
                if invs_19_global and 'amount_discount' in invs_19_global[0]:
                    o19_global_discount = invs_19_global[0]['amount_discount'] or 0.0
            except Exception:
                pass
                
            total_o14_discount = o14_discount_amount + o14_global_discount
            total_o19_discount = o19_discount_amount + o19_global_discount
            
            # Fix logic
            needs_fix = False
            lines_to_modify = []
            
            for l19 in lines_19:
                if l19.get('display_type'):
                    continue
                    
                # Try to find corresponding line in 14 by product or name
                matched_l14 = next((l for l in lines_14 if l['product_id'] and l19['product_id'] and l['product_id'][1] == l19['product_id'][1]), None)
                if not matched_l14:
                    matched_l14 = next((l for l in lines_14 if l['name'] == l19['name']), None)
                    
                if matched_l14:
                    disc_14 = matched_l14.get('discount', 0.0) or 0.0
                    disc_19 = l19.get('discount', 0.0) or 0.0
                    
                    if abs(disc_14 - disc_19) > 0.001:
                        _logger.info(f"  [{inv_name}] Line '{l19['name']}' has discount {disc_14}% in O14 but {disc_19}% in O19.")
                        needs_fix = True
                        lines_to_modify.append((1, l19['id'], {'discount': disc_14}))
            
            status = 'Needs manual review'
            
            if abs(total_o14_discount - total_o19_discount) <= 0.01:
                status = 'Match'
                
            elif needs_fix:
                if args.fix:
                    try:
                        # Set to draft
                        try:
                            models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'button_draft', [[inv_19['id']]])
                        except Exception as e:
                            if 'marshal None' not in str(e):
                                raise
                        
                        # Apply line changes
                        models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'write', [[inv_19['id']], {'invoice_line_ids': lines_to_modify}])
                        
                        # Post again if it was posted
                        if inv_19['state'] == 'posted':
                            try:
                                models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'action_post', [[inv_19['id']]])
                            except Exception as e:
                                if 'marshal None' not in str(e):
                                    raise
                        
                        status = 'Fixed'
                        _logger.info(f"  {inv_name} fixed successfully.")
                    except Exception as e:
                        _logger.error(f"Failed to fix {inv_name}: {e}")
                        status = f'Error fixing: {str(e)}'
                else:
                    status = 'Mismatch (Can be fixed via --fix)'
            
            if total_o14_discount > 0.01 or total_o19_discount > 0.01 or status != 'Match':
                # Create exact columns requested
                o14_discount_str = f"Amt: {round(total_o14_discount, 2)}"
                if o14_discount_pcts:
                    o14_discount_str += f" (Lines: {','.join(o14_discount_pcts)})"
                    
                o19_discount_str = f"Amt: {round(total_o19_discount, 2)}"
                if o19_discount_pcts:
                    o19_discount_str += f" (Lines: {','.join(o19_discount_pcts)})"

                all_results.append({
                    'Company': company_name,
                    'Invoice Number': inv_name,
                    'odoo14 discount': o14_discount_str,
                    'odoo19 discount': o19_discount_str,
                    'Original Odoo 14 Total': inv14_total,
                    'Odoo 19 Total Before': inv19_total_before,
                    'Status': status
                })
            
    # Export report
    if all_results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        company_suffix = args.company_name.replace(' ', '_') if args.company_name else 'ALL_COMPANIES'
        report_name = f"customer_invoice_discounts_report_{company_suffix}_{timestamp}.xlsx"
        pd.DataFrame(all_results).to_excel(report_name, index=False)
        _logger.info(f"Audit report saved: {report_name}")
    else:
        _logger.info("No discount mismatches or invoices with discounts found in the tested batch.")

if __name__ == "__main__":
    main()
