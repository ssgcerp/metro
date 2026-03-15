import xmlrpc.client
import ssl
import pandas as pd
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

REPORT_PATH = r"e:\odoo modules\19\metro\odoo14_to_19_migration\tools\Migration\vendor_bill_tax_fix_o18_report_ALL_20260314_212921.xlsx"

def get_odoo_client(url, db, username, password):
    ctx = ssl._create_unverified_context()
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ctx, allow_none=True)
    uid = common.authenticate(db, username, password, {})
    if not uid:
        raise Exception(f"Failed to authenticate to {url}")
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ctx, allow_none=True)
    return uid, models

def main():
    _logger.info("Reading report to find manual review bills...")
    df = pd.read_excel(REPORT_PATH)
    manual_df = df[df['Status'] == 'Needs manual review']
    bill_names = manual_df['Odoo 19 Bill Number'].tolist()
    
    _logger.info(f"Targeting {len(bill_names)} bills for specialized fixing.")
    
    _logger.info("Connecting to Odoo...")
    uid_18, models_18 = get_odoo_client(URL_18, DB_18, USER_18, PASS_18)
    uid_19, models_19 = get_odoo_client(URL_19, DB_19, USER_19, PASS_19)

    results = []
    
    # Pre-fetch O18 data for these specific bills
    o18_data_map = {}
    batch_size = 200
    for i in range(0, len(bill_names), batch_size):
        batch = bill_names[i:i+batch_size]
        domain_18 = [('move_type', '=', 'in_invoice'), ('name', 'in', batch)]
        res = models_18.execute_kw(DB_18, uid_18, PASS_18, 'account.move', 'search_read', [domain_18],
                                   {'fields': ['name', 'amount_total', 'invoice_line_ids']})
        for r in res:
            o18_data_map[r['name']] = r

    # Fetch O19 details
    invs_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'search_read', 
                                    [[('move_type', '=', 'in_invoice'), ('name', 'in', bill_names)]],
                                    {'fields': ['name', 'amount_total', 'invoice_line_ids', 'state']})

    for inv_19 in invs_19:
        inv_name = inv_19['name']
        inv_18 = o18_data_map.get(inv_name)
        
        if not inv_18:
            continue
            
        inv18_total = inv_18['amount_total']
        inv19_total_before = inv_19['amount_total']
        
        _logger.info(f"Analyzing {inv_name} (O18: {inv18_total}, O19: {inv19_total_before})")
        
        lines_18 = models_18.execute_kw(DB_18, uid_18, PASS_18, 'account.move.line', 'search_read',
                                        [[('id', 'in', inv_18['invoice_line_ids'])]],
                                        {'fields': ['product_id', 'name', 'tax_ids', 'price_unit', 'quantity']})

        lines_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move.line', 'search_read',
                                        [[('id', 'in', inv_19['invoice_line_ids']), ('display_type', '=', 'product')]],
                                        {'fields': ['product_id', 'name', 'tax_ids', 'price_unit', 'quantity']})

        lines_to_modify = []
        needs_fix = False
        
        for l19 in lines_19:
            # 1. Flexible Match: By Product ID Name
            m = next((l for l in lines_18 if l['product_id'] and l19['product_id'] and l['product_id'][1] == l19['product_id'][1]), None)
            
            # 2. Match by Name Trimmed
            if not m:
                m = next((l for l in lines_18 if l['name'] and l19['name'] and l['name'].strip().lower() == l19['name'].strip().lower()), None)
            
            # 3. Match by Price and Quantity
            if not m:
                m = next((l for l in lines_18 if abs(l['price_unit'] - l19['price_unit']) < 0.01 and abs(l['quantity'] - l19['quantity']) < 0.001), None)

            if m:
                updates = {}
                # If O18 has NO tax and O19 HAS tax
                if not m['tax_ids'] and l19['tax_ids']:
                    _logger.info(f"    Targeting line '{l19['name']}': clearing spurious tax.")
                    updates['tax_ids'] = [(5, 0, 0)]
                
                # Sync quantity/price if different
                if abs(l19['quantity'] - m['quantity']) > 0.001:
                    updates['quantity'] = m['quantity']
                if abs(l19['price_unit'] - m['price_unit']) > 0.01:
                    updates['price_unit'] = m['price_unit']
                
                if updates:
                    needs_fix = True
                    lines_to_modify.append((1, l19['id'], updates))

        if needs_fix:
            try:
                if inv_19['state'] != 'draft':
                    try:
                        models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'button_draft', [[inv_19['id']]])
                    except Exception as e:
                        if 'marshal None' not in str(e): raise
                
                models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'write', [[inv_19['id']], {'invoice_line_ids': lines_to_modify}])
                
                try:
                    models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'action_post', [[inv_19['id']]])
                except Exception as e:
                    if 'marshal None' not in str(e): raise
                
                updated_inv = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'read', [[inv_19['id']]], {'fields': ['amount_total']})[0]
                final_total = updated_inv['amount_total']
                
                status = "Fixed" if abs(final_total - inv18_total) < 0.01 else "Partial Fix"
                _logger.info(f"  Result for {inv_name}: {status} (New Total: {final_total})")
                
                results.append({
                    'Bill': inv_name,
                    'O18 Total': inv18_total,
                    'O19 Before': inv19_total_before,
                    'O19 After': final_total,
                    'Status': status
                })
            except Exception as e:
                _logger.error(f"  Error fixing {inv_name}: {e}")
                results.append({'Bill': inv_name, 'Status': f'Error: {e}'})
        else:
            _logger.warning(f"  Could not find clear lines to fix for {inv_name}")
            results.append({'Bill': inv_name, 'Status': 'Still needs review'})

    if results:
        pd.DataFrame(results).to_excel("manual_review_fix_results.xlsx", index=False)
        _logger.info("Fix results saved to manual_review_fix_results.xlsx")

if __name__ == "__main__":
    main()
