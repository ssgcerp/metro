import xmlrpc.client
import ssl
import pandas as pd
import argparse
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

# Odoo 18 Credentials (Source)
URL_18 = "https://metro-fire-system-llc.odoo.com"
DB_18 = "metro-fire-system-llc"
USER_18 = "sruthi@metrofiresystems.com"
PASS_18 = "Sruthi@321"

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
    parser = argparse.ArgumentParser(description='Verify and Fix Vendor Bill Taxes (Odoo 18 -> Odoo 19)')
    parser.add_argument('--limit', type=int, default=10000, help='Max bills to process')
    args = parser.parse_args()

    _logger.info("Connecting to Odoo instances...")
    uid_18, models_18 = get_odoo_client(URL_18, DB_18, USER_18, PASS_18)
    uid_19, models_19 = get_odoo_client(URL_19, DB_19, USER_19, PASS_19)

    # Search for vendor bills in Odoo 19 - ALL companies, posted OR draft
    domain_19 = [('move_type', '=', 'in_invoice'), ('state', 'in', ['posted', 'draft'])]
    invs_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'search_read', [domain_19],
                                   {'fields': ['name', 'amount_total', 'invoice_line_ids', 'state', 'company_id'], 
                                    'limit': args.limit, 'order': 'id desc'})

    total_o19 = len(invs_19)
    _logger.info(f"Found {total_o19} vendor bills to verify in Odoo 19 (All Companies)")

    if not invs_19:
        return

    # Pre-fetch matching bills from Odoo 18 in bulk batches
    o19_names = [inv['name'] for inv in invs_19 if inv['name']]
    o18_data_map = {}
    
    batch_size = 200
    _logger.info(f"Checking Odoo 18 for {len(o19_names)} bills in batches...")
    for i in range(0, len(o19_names), batch_size):
        batch = o19_names[i:i+batch_size]
        domain_18 = [('move_type', '=', 'in_invoice'), ('name', 'in', batch)]
        results = models_18.execute_kw(DB_18, uid_18, PASS_18, 'account.move', 'search_read', [domain_18],
                                       {'fields': ['name', 'amount_total', 'invoice_line_ids']})
        for r in results:
            o18_data_map[r['name']] = r
        _logger.info(f"  Processed {i + len(batch)} names...")

    results = []
    processed_count = 0

    for inv_19 in invs_19:
        processed_count += 1
        inv_name = inv_19['name']
        if processed_count % 50 == 0:
            _logger.info(f"Progress: {processed_count}/{total_o19} bills analyzed")

        # Odoo 19 info
        inv19_total_before = inv_19['amount_total']
        
        inv_18 = o18_data_map.get(inv_name)

        if not inv_18:
            # We skip reporting "Skipped" for everything to keep log clean, 
            # but we add it to results for the Excel report.
            results.append({
                'Odoo 18 Bill Number': 'N/A',
                'Odoo 19 Bill Number': inv_name,
                'Original Odoo 18 Total': 'N/A',
                'Odoo 19 Total Before': inv19_total_before,
                'Final Odoo 19 Total': inv19_total_before,
                'Status': 'Skipped - Not found in O18'
            })
            continue

        inv18_total = inv_18['amount_total']

        if abs(inv19_total_before - inv18_total) < 0.01:
            results.append({
                'Odoo 18 Bill Number': inv_name,
                'Odoo 19 Bill Number': inv_name,
                'Original Odoo 18 Total': inv18_total,
                'Odoo 19 Total Before': inv19_total_before,
                'Final Odoo 19 Total': inv19_total_before,
                'Status': 'No changes'
            })
            continue

        _logger.info(f"Mismatch [{processed_count}/{total_o19}] on {inv_name}: O18={inv18_total}, O19={inv19_total_before}. Analyzing lines...")

        # Get lines detailed info
        lines_18 = models_18.execute_kw(DB_18, uid_18, PASS_18, 'account.move.line', 'search_read',
                                        [[('id', 'in', inv_18['invoice_line_ids'])]],
                                        {'fields': ['product_id', 'name', 'tax_ids', 'price_unit', 'quantity']})

        lines_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move.line', 'search_read',
                                        [[('id', 'in', inv_19['invoice_line_ids']), ('display_type', '=', 'product')]],
                                        {'fields': ['product_id', 'name', 'tax_ids', 'price_unit', 'quantity']})

        needs_fix = False
        lines_to_modify = []

        for l19 in lines_19:
            # Match by product or name
            matched_l18 = next((l for l in lines_18 if l['product_id'] and l19['product_id'] and l['product_id'][1] == l19['product_id'][1]), None)
            if not matched_l18:
                matched_l18 = next((l for l in lines_18 if l['name'] == l19['name']), None)

            if matched_l18:
                line_updates = {}
                
                # Sync Quantity
                if abs(l19['quantity'] - matched_l18['quantity']) > 0.001:
                    _logger.info(f"    Line '{l19['name']}': quantity {l19['quantity']} -> {matched_l18['quantity']}")
                    line_updates['quantity'] = matched_l18['quantity']
                
                # Sync Price Unit
                if abs(l19['price_unit'] - matched_l18['price_unit']) > 0.001:
                    _logger.info(f"    Line '{l19['name']}': price_unit {l19['price_unit']} -> {matched_l18['price_unit']}")
                    line_updates['price_unit'] = matched_l18['price_unit']

                # Odoo 18 had NO taxes on this line, but Odoo 19 HAS taxes
                if not matched_l18['tax_ids'] and l19['tax_ids']:
                    _logger.info(f"    Line '{l19['name']}': clearing taxes")
                    line_updates['tax_ids'] = [(5, 0, 0)]
                
                if line_updates:
                    needs_fix = True
                    lines_to_modify.append((1, l19['id'], line_updates))

        if needs_fix:
            try:
                # Set to draft only if currently posted
                if inv_19.get('state') != 'draft':
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
                if abs(final_total - inv18_total) > 0.01:
                    status = 'Fixed, but total still differs'
                    _logger.warning(f"    {inv_name} fixed, but O19 Total ({final_total}) != O18 Total ({inv18_total})")
                else:
                    _logger.info(f"    {inv_name} fixed successfully. New total: {final_total}")

                results.append({
                    'Odoo 18 Bill Number': inv_name,
                    'Odoo 19 Bill Number': inv_name,
                    'Original Odoo 18 Total': inv18_total,
                    'Odoo 19 Total Before': inv19_total_before,
                    'Final Odoo 19 Total': final_total,
                    'Status': status
                })

            except Exception as e:
                _logger.error(f"Failed to fix {inv_name}: {e}")
                results.append({
                    'Odoo 18 Bill Number': inv_name,
                    'Odoo 19 Bill Number': inv_name,
                    'Original Odoo 18 Total': inv18_total,
                    'Odoo 19 Total Before': inv19_total_before,
                    'Final Odoo 19 Total': inv19_total_before,
                    'Status': f'Error: {e}'
                })
        else:
            results.append({
                'Odoo 18 Bill Number': inv_name,
                'Odoo 19 Bill Number': inv_name,
                'Original Odoo 18 Total': inv18_total,
                'Odoo 19 Total Before': inv19_total_before,
                'Final Odoo 19 Total': inv19_total_before,
                'Status': 'Needs manual review'
            })

    # Export report
    if results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_name = f"vendor_bill_tax_fix_o18_report_ALL_{timestamp}.xlsx"
        pd.DataFrame(results).to_excel(report_name, index=False)
        _logger.info(f"Audit report saved: {report_name}")

if __name__ == "__main__":
    main()
