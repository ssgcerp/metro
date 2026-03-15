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
    parser = argparse.ArgumentParser(description='Compare Odoo 14 and Odoo 19 Customer Invoices')
    parser.add_argument('--limit', type=int, default=1000, help='Batch size for testing per Odoo 14 customer company')
    parser.add_argument('--offset', type=int, default=0, help='Offset for testing per Odoo 14 customer company')
    args = parser.parse_args()

    _logger.info("Connecting to Odoo instances...")
    try:
        uid_14, models_14 = get_odoo_client(URL_14, DB_14, USER_14, PASS_14)
        uid_19, models_19 = get_odoo_client(URL_19, DB_19, USER_19, PASS_19)
    except Exception as e:
        _logger.error(f"Failed to connect to Odoo: {e}")
        return

    # 1. Fetch all Odoo 14 customer invoices (out_invoice)
    # Filter for posted and draft invoices?
    domain_14 = [('move_type', '=', 'out_invoice')]
    _logger.info(f"Fetching Odoo 14 customer invoices (limit={args.limit}, offset={args.offset})...")
    
    try:
        invs_14 = models_14.execute_kw(DB_14, uid_14, PASS_14, 'account.move', 'search_read', [domain_14], 
                                    {'fields': ['name', 'amount_total', 'amount_discount', 'invoice_line_ids', 'company_id', 'state'], 
                                     'limit': args.limit, 'offset': args.offset, 'order': 'id desc'})
    except Exception as e:
        _logger.error(f"Failed to fetch Odoo 14 invoices: {e}")
        return
                                    
    _logger.info(f"Found {len(invs_14)} invoices in Odoo 14 to compare.")

    results = []
    
    # Optional: fetch all O19 invoices into memory if the list is small, but for 2k+ it's better to query individually or in chunks.
    # To optimize, let's collect all O14 names and perform one huge O19 search.
    inv_names_14 = [inv['name'] for inv in invs_14 if inv.get('name') and inv['name'] != '/']
    
    _logger.info(f"Extracted {len(inv_names_14)} named invoices. Fetching matches from Odoo 19...")
    
    # We chunk the search because of potential URL length limits in XMLRPC
    chunk_size = 500
    invs_19_dict = {}
    lines_19_all = {}
    
    for i in range(0, len(inv_names_14), chunk_size):
        chunk_names = inv_names_14[i:i+chunk_size]
        try:
            domain_19 = [('move_type', '=', 'out_invoice'), ('name', 'in', chunk_names)]
            invs_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'search_read', [domain_19], 
                                          {'fields': ['name', 'amount_total', 'invoice_line_ids', 'state']})
                                          
            for inv19 in invs_19:
                invs_19_dict[inv19['name']] = inv19
        except Exception as e:
             _logger.warning(f"Error fetching Odoo 19 chunk {i}-{i+chunk_size}: {e}")

    _logger.info(f"Found {len(invs_19_dict)} matching invoices in Odoo 19.")

    for idx, inv_14 in enumerate(invs_14):
        inv_name = inv_14.get('name')
        
        # We need a proper name to compare
        if not inv_name or inv_name == '/':
            continue
            
        if idx % 100 == 0 and idx > 0:
            _logger.info(f"Processed {idx}/{len(invs_14)} invoices...")

        odoo14_company = inv_14['company_id'][1] if inv_14.get('company_id') else ''
        odoo14_status = inv_14.get('state', '')

        # Odoo 14 Discount Calculation
        # Line level + global
        o14_discount_amount = 0.0
        try:
            if inv_14.get('invoice_line_ids'):
                lines_14 = models_14.execute_kw(DB_14, uid_14, PASS_14, 'account.move.line', 'read', 
                                               [inv_14['invoice_line_ids']], 
                                               {'fields': ['discount', 'price_unit', 'quantity', 'display_type']})
                for l in lines_14:
                    if not l.get('display_type') and l.get('discount'):
                        disc = l['discount']
                        qty = l.get('quantity', 0.0)
                        price = l.get('price_unit', 0.0)
                        amount = qty * price * (disc / 100.0)
                        o14_discount_amount += amount
        except Exception as e:
            _logger.warning(f"Failed to read lines for {inv_name} in O14: {e}")
            
        o14_global_discount = inv_14.get('amount_discount') or 0.0
        total_o14_discount = o14_discount_amount + o14_global_discount

        # Check Odoo 19
        inv_19 = invs_19_dict.get(inv_name)
        
        if not inv_19:
            results.append({
                'Odoo 14 Invoice': inv_name,
                'Odoo 19 Total': 'Not in Odoo 19',
                'Odoo 14 Discount': round(total_o14_discount, 2),
                'Odoo 19 Discount': 'Not in Odoo 19',
                'Remarks': 'Not in Odoo 19',
                'Odoo 14 Company': odoo14_company,
                'Odoo 14 Status': odoo14_status
            })
            continue
            
        # Invoice exists in Odoo 19, calculate discount
        o19_total = inv_19.get('amount_total', 0.0)
        
        o19_discount_amount = 0.0
        try:
            if inv_19.get('invoice_line_ids'):
                lines_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move.line', 'read', 
                                               [inv_19['invoice_line_ids']], 
                                               {'fields': ['discount', 'price_unit', 'quantity', 'display_type']})
                for l in lines_19:
                    if not l.get('display_type') and l.get('discount'):
                        disc = l['discount']
                        qty = l.get('quantity', 0.0)
                        price = l.get('price_unit', 0.0)
                        amount = qty * price * (disc / 100.0)
                        o19_discount_amount += amount
        except Exception as e:
             _logger.warning(f"Failed to read lines for {inv_name} in O19: {e}")
             
        o19_global_discount = inv_19.get('amount_discount') or 0.0
        total_o19_discount = o19_discount_amount + o19_global_discount
        
        remarks = 'Matched'
        diff_total = abs(inv_14.get('amount_total', 0.0) - o19_total)
        diff_discount = abs(total_o14_discount - total_o19_discount)
        
        issues = []
        if diff_total > 0.01:
            issues.append(f"Total mismatch (O14: {round(inv_14.get('amount_total', 0.0), 2)} vs O19: {round(o19_total, 2)})")
        if diff_discount > 0.01:
            issues.append("Discount mismatch")
            
        if issues:
            remarks = " & ".join(issues)
            
        results.append({
            'Odoo 14 Invoice': inv_name,
            'Odoo 19 Total': round(o19_total, 2),
            'Odoo 14 Discount': round(total_o14_discount, 2),
            'Odoo 19 Discount': round(total_o19_discount, 2),
            'Remarks': remarks,
            'Odoo 14 Company': odoo14_company,
            'Odoo 14 Status': odoo14_status
        })
        
    # Export report
    if results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_name = f"odoo14_vs_odoo19_invoice_comparison_{timestamp}.xlsx"
        df = pd.DataFrame(results)
        
        # Reorder columns exactly as user requested 
        cols = ['Odoo 14 Invoice', 'Odoo 19 Total', 'Odoo 14 Discount', 'Odoo 19 Discount', 'Remarks', 'Odoo 14 Company', 'Odoo 14 Status']
        df = df[[c for c in cols if c in df.columns]]
        
        df.to_excel(report_name, index=False)
        _logger.info(f"Invoice comparison report saved: {report_name}")
    else:
        _logger.info("No valid invoices processed.")

if __name__ == "__main__":
    main()
