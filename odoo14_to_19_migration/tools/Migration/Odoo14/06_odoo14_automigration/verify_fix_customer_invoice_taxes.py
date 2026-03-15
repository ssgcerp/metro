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
    parser = argparse.ArgumentParser(description='Verify and Fix Customer Invoice Taxes (Odoo 14 -> Odoo 19)')
    parser.add_argument('--limit', type=int, default=50, help='Batch size for testing')
    parser.add_argument('--company-name', type=str, required=True, help='Company name in Odoo 19')
    args = parser.parse_args()

    _logger.info("Connecting to Odoo instances...")
    uid_14, models_14 = get_odoo_client(URL_14, DB_14, USER_14, PASS_14)
    uid_19, models_19 = get_odoo_client(URL_19, DB_19, USER_19, PASS_19)

    # 1. Get Company ID in Odoo 19
    company_search = models_19.execute_kw(DB_19, uid_19, PASS_19, 'res.company', 'search_read', [[('name', '=', args.company_name)]], {'fields': ['id'], 'limit': 1})
    if not company_search:
        _logger.error(f"Company {args.company_name} not found in Odoo 19")
        return
    company_id_19 = company_search[0]['id']

    # 2. Search for posted out_invoices in Odoo 19 for this company
    domain_19 = [('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('company_id', '=', company_id_19)]
    invs_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'search_read', [domain_19], 
                                  {'fields': ['name', 'amount_total', 'invoice_line_ids', 'state'], 'limit': args.limit, 'order': 'id desc'})
    
    _logger.info(f"Found {len(invs_19)} invoices to verify in Odoo 19 (Company: {args.company_name})")

    results = []

    for inv_19 in invs_19:
        inv_name = inv_19['name']
        
        # Odoo 19 info
        inv19_total_before = inv_19['amount_total']
        
        # 3. Find matching invoice in Odoo 14
        domain_14 = [('move_type', '=', 'out_invoice'), ('name', '=', inv_name)]
        invs_14 = models_14.execute_kw(DB_14, uid_14, PASS_14, 'account.move', 'search_read', [domain_14], 
                                      {'fields': ['name', 'amount_total', 'invoice_line_ids']})
        
        if not invs_14:
            _logger.warning(f"Invoice {inv_name} not found in Odoo 14. Skipping.")
            results.append({
                'Odoo 14 Invoice Number': 'N/A',
                'Odoo 19 Invoice Number': inv_name,
                'Original Odoo 14 Total': 'N/A',
                'Odoo 19 Total Before': inv19_total_before,
                'Final Odoo 19 Total': inv19_total_before,
                'Status': 'Skipped - Not found in O14'
            })
            continue
            
        inv_14 = invs_14[0]
        inv14_total = inv_14['amount_total']
        
        if abs(inv19_total_before - inv14_total) < 0.01:
            # Already matches perfectly, no tax fix needed
            results.append({
                'Odoo 14 Invoice Number': inv_name,
                'Odoo 19 Invoice Number': inv_name,
                'Original Odoo 14 Total': inv14_total,
                'Odoo 19 Total Before': inv19_total_before,
                'Final Odoo 19 Total': inv19_total_before,
                'Status': 'No changes'
            })
            continue
            
        _logger.info(f"Mismatch found on {inv_name}: O14={inv14_total}, O19={inv19_total_before}. Analyzing lines...")
        
        # Get lines detailed info
        lines_14 = models_14.execute_kw(DB_14, uid_14, PASS_14, 'account.move.line', 'search_read', 
                                       [[('id', 'in', inv_14['invoice_line_ids'])]], 
                                       {'fields': ['product_id', 'name', 'tax_ids', 'price_unit', 'quantity']})
                                       
        lines_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move.line', 'search_read', 
                                       [[('id', 'in', inv_19['invoice_line_ids']), ('display_type', '=', 'product')]], 
                                       {'fields': ['product_id', 'name', 'tax_ids', 'price_unit', 'quantity']})
        
        needs_fix = False
        lines_to_modify = []
        
        for l19 in lines_19:
            # Try to find corresponding line in 14 by product or name
            matched_l14 = next((l for l in lines_14 if l['product_id'] and l19['product_id'] and l['product_id'][1] == l19['product_id'][1]), None)
            if not matched_l14:
                matched_l14 = next((l for l in lines_14 if l['name'] == l19['name']), None)
                
            if matched_l14:
                # Odoo 14 had NO taxes on this line, but Odoo 19 HAS taxes
                if not matched_l14['tax_ids'] and l19['tax_ids']:
                    _logger.info(f"  Line '{l19['name']}' has taxes in O19 but none in O14. Marking for removal.")
                    needs_fix = True
                    lines_to_modify.append((1, l19['id'], {'tax_ids': [(5, 0, 0)]})) # Command 5 = clear all taxes
        
        if needs_fix:
            try:
                # Set to draft
                try:
                    models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'button_draft', [[inv_19['id']]])
                except Exception as e:
                    if 'marshal None' not in str(e):
                        raise
                
                # Apply line changes
                models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'write', [[inv_19['id']], {'invoice_line_ids': lines_to_modify}])
                
                # Post again
                try:
                    models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'action_post', [[inv_19['id']]])
                except Exception as e:
                    if 'marshal None' not in str(e):
                        raise
                        
                # Verify new total
                updated_inv = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'read', [[inv_19['id']]], {'fields': ['amount_total']})[0]
                final_total = updated_inv['amount_total']
                
                status = 'Fixed'
                if abs(final_total - inv14_total) > 0.01:
                    status = 'Fixed, but total still differs'
                    _logger.warning(f"  {inv_name} fixed, but O19 Total ({final_total}) != O14 Total ({inv14_total})")
                else:
                    _logger.info(f"  {inv_name} fixed successfully. New total: {final_total}")
                
                results.append({
                    'Odoo 14 Invoice Number': inv_name,
                    'Odoo 19 Invoice Number': inv_name,
                    'Original Odoo 14 Total': inv14_total,
                    'Odoo 19 Total Before': inv19_total_before,
                    'Final Odoo 19 Total': final_total,
                    'Status': status
                })
                
            except Exception as e:
                _logger.error(f"Failed to fix {inv_name}: {e}")
                results.append({
                    'Odoo 14 Invoice Number': inv_name,
                    'Odoo 19 Invoice Number': inv_name,
                    'Original Odoo 14 Total': inv14_total,
                    'Odoo 19 Total Before': inv19_total_before,
                    'Final Odoo 19 Total': inv19_total_before,
                    'Status': f'Error: {e}'
                })
        else:
            # Totals differed, but no specific zero-tax match was found to fix, or it was unhandled
            results.append({
                'Odoo 14 Invoice Number': inv_name,
                'Odoo 19 Invoice Number': inv_name,
                'Original Odoo 14 Total': inv14_total,
                'Odoo 19 Total Before': inv19_total_before,
                'Final Odoo 19 Total': inv19_total_before,
                'Status': 'Needs manual review'
            })
            
    # Export report
    if results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_name = f"invoice_tax_fix_report_{args.company_name.replace(' ', '_')}_{timestamp}.xlsx"
        pd.DataFrame(results).to_excel(report_name, index=False)
        _logger.info(f"Audit report saved: {report_name}")

if __name__ == "__main__":
    main()
