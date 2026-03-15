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

def get_odoo14_client(url, db, username, password):
    """Returns a server proxy and uid for Odoo 14 XML-RPC."""
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
        uid = common.authenticate(db, username, password, {})
        if not uid:
            return None, None
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())
        return models, uid
    except Exception as e:
        _logger.error(f"Failed to connect to Odoo 14: {e}")
        return None, None

def main():
    parser = argparse.ArgumentParser(description='Generate Odoo 14 Journal Mapping Excel')
    parser.add_argument('--output', default='journal_mapping_o14.xlsx', help='Output Excel filename')
    args = parser.parse_args()

    _logger.info(f"Connecting to Odoo 14 at {URL_14}...")
    models, uid = get_odoo14_client(URL_14, DB_14, USER_14, PASS_14)
    if not uid:
        _logger.error("Authentication failed.")
        return

    _logger.info("Fetching inbound payments for journal mapping...")
    # Domain: inbound customer payments
    domain = [
        ('payment_type', '=', 'inbound'),
        ('partner_type', '=', 'customer'),
    ]
    
    # In Odoo 14 Metro, 'branch_id' is used for company separation
    fields = ['journal_id', 'branch_id']
    
    try:
        payments = models.execute_kw(DB_14, uid, PASS_14, 'account.payment', 'search_read', [domain], {'fields': fields})
        _logger.info(f"Retrieved {len(payments)} payments.")
    except Exception as e:
        _logger.error(f"Error fetching payments: {e}")
        return

    if not payments:
        _logger.warning("No payments found with the given criteria.")
        return

    # Aggregate data
    mapping_data = {}
    for p in payments:
        journal = p.get('journal_id')
        branch = p.get('branch_id')
        
        if not journal:
            continue
            
        journal_id = journal[0]
        journal_name = journal[1]
        branch_name = branch[1] if branch else 'Unknown Branch'
        
        key = (journal_id, branch_name)
        if key not in mapping_data:
            mapping_data[key] = {
                'Source Journal ID': journal_id,
                'Source Journal Name': journal_name,
                'Source Company': branch_name,
                'Total No. of Payments': 0,
                'Dest Journal ID': '',
                'Dest Journal Name': '',
                'Dest Company': '',
                'Parent Company': ''
            }
        mapping_data[key]['Total No. of Payments'] += 1

    # Convert to list and then DataFrame
    final_data = list(mapping_data.values())
    df = pd.DataFrame(final_data)
    
    # Sort by Source Company and Journal Name
    df = df.sort_values(by=['Source Company', 'Source Journal Name'])

    # Export to Excel
    _logger.info(f"Saving mapping to {args.output}...")
    df.to_excel(args.output, index=False)
    _logger.info("Successfully generated Odoo 14 Journal Mapping Excel.")

if __name__ == "__main__":
    main()
