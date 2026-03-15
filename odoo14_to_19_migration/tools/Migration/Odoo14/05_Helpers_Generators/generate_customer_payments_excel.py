import xmlrpc.client
import ssl
import pandas as pd
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
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
    """Returns a server proxy and uid for Odoo XML-RPC."""
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
    uid = common.authenticate(db, username, password, {})
    if not uid:
        return None, None
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())
    return models, uid

def fetch_payments(models, db, uid, password, limit=None):
    """Fetches customer inbound payments."""
    domain = [
        ('payment_type', '=', 'inbound'),
        ('partner_type', '=', 'customer'),
    ]
    fields = ['name', 'date', 'amount', 'state', 'partner_id', 'journal_id', 'communication']
    
    # communication in Odoo 19 might be 'ref' or 'memo' depending on the version/module
    # In Odoo 14 it's usually 'communication' or 'name' (ref is also common)
    # We'll try to fetch common ones and handle missing
    try:
        # Check if 'memo' exists or 'ref'
        # For simplicity, we'll fetch a broad set and handle results
        available_fields = models.execute_kw(db, uid, password, 'account.payment', 'fields_get', [], {'attributes': ['string']})
        
        target_fields = ['name', 'date', 'amount', 'state', 'partner_id', 'journal_id']
        if 'communication' in available_fields: target_fields.append('communication')
        if 'ref' in available_fields: target_fields.append('ref')
        if 'memo' in available_fields: target_fields.append('memo')
        if 'branch_id' in available_fields: target_fields.append('branch_id')
        if 'company_id' in available_fields: target_fields.append('company_id')

        search_kwargs = {'fields': target_fields, 'order': 'date desc'}
        if limit:
            search_kwargs['limit'] = limit

        payments = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [domain], search_kwargs)
        return payments
    except Exception as e:
        _logger.error(f"Error fetching payments: {e}")
        return []

def process_payments_to_df(payments):
    """Converts payment list to a clean DataFrame."""
    if not payments:
        return pd.DataFrame()
    
    data = []
    for p in payments:
        row = {
            'Name': p.get('name'),
            'Date': p.get('date'),
            'Amount': p.get('amount'),
            'State': p.get('state'),
            'Partner': p.get('partner_id')[1] if p.get('partner_id') else '',
            'Journal': p.get('journal_id')[1] if p.get('journal_id') else '',
            'Memo/Ref': p.get('communication') or p.get('ref') or p.get('memo') or '',
            'Company/Branch': (p.get('branch_id')[1] if p.get('branch_id') else '') or (p.get('company_id')[1] if p.get('company_id') else '')
        }
        data.append(row)
    
    return pd.DataFrame(data)

def main():
    parser = argparse.ArgumentParser(description='Generate Customer Payments Excel for Odoo 14 and 19')
    parser.add_argument('--limit', type=int, help='Limit number of records to fetch per server')
    parser.add_argument('--output', default='customer_payments_comparison.xlsx', help='Output filename')
    args = parser.parse_args()

    # Odoo 14
    _logger.info(f"Connecting to Odoo 14 at {URL_14}...")
    models_14, uid_14 = get_odoo_client(URL_14, DB_14, USER_14, PASS_14)
    if not uid_14:
        _logger.error("Failed to authenticate with Odoo 14.")
        return
    
    _logger.info("Fetching Odoo 14 payments...")
    payments_14 = fetch_payments(models_14, DB_14, uid_14, PASS_14, limit=args.limit)
    df_14 = process_payments_to_df(payments_14)
    _logger.info(f"Found {len(df_14)} payments in Odoo 14.")

    # Odoo 19
    _logger.info(f"Connecting to Odoo 19 at {URL_19}...")
    models_19, uid_19 = get_odoo_client(URL_19, DB_19, USER_19, PASS_19)
    if not uid_19:
        _logger.warning("Failed to authenticate with Odoo 19. Trying 'metrodb' as fallback...")
        models_19, uid_19 = get_odoo_client(URL_19, 'metrodb', USER_19, PASS_19)
        if uid_19:
            db_19_actual = 'metrodb'
        else:
            _logger.error("Failed to authenticate with Odoo 19.")
            return
    else:
        db_19_actual = DB_19

    _logger.info(f"Fetching Odoo 19 payments from {db_19_actual}...")
    payments_19 = fetch_payments(models_19, db_19_actual, uid_19, PASS_19, limit=args.limit)
    df_19 = process_payments_to_df(payments_19)
    _logger.info(f"Found {len(df_19)} payments in Odoo 19.")

    # Save to Excel
    _logger.info(f"Saving to {args.output}...")
    with pd.ExcelWriter(args.output) as writer:
        df_14.to_excel(writer, sheet_name='Odoo 14 Payments', index=False)
        df_19.to_excel(writer, sheet_name='Odoo 19 Payments', index=False)
    
    _logger.info("Successfully generated Excel report.")

if __name__ == "__main__":
    main()
