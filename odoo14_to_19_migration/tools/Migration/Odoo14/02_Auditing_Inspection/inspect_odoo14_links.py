
import xmlrpc.client
import logging
import argparse

# Odoo 14 Credentials
URL = "https://erpmfs.com"
DB = "metro_production_8_8_22"
USER = "Sales.auh@metrofiresystems.com"
PASS = "Sales@185734"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def inspect_links():
    try:
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL))
        uid = common.authenticate(DB, USER, PASS, {})
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL))

        logger.info("Connected to Odoo 14.")

        # Find POs with POSTED invoices
        logger.info("Searching for POs with POSTED invoices...")
        pos = models.execute_kw(DB, uid, PASS, 'purchase.order', 'search_read', 
            [[('state', 'in', ['purchase', 'done']), ('invoice_count', '>', 0)]], 
            {'fields': ['name', 'invoice_ids'], 'limit': 20})

        for po in pos:
            if po['invoice_ids']:
                # Fetch Invoice Details, Filter for POSTED
                inv_ids = po['invoice_ids']
                invoices = models.execute_kw(DB, uid, PASS, 'account.move', 'search_read', 
                    [[('id', 'in', inv_ids), ('state', '=', 'posted'), ('move_type', '=', 'in_invoice')]], 
                    {'fields': ['name', 'ref', 'invoice_origin', 'name']})
                
                if invoices:
                    logger.info(f"PO: {po['name']} has posted bills:")
                    for inv in invoices:
                        logger.info(f"  -> Bill: {inv['name']} | Ref: {inv['ref']} | Origin: {inv['invoice_origin']}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    inspect_links()
