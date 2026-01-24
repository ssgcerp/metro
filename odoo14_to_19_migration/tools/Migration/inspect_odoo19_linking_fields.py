
import xmlrpc.client
import logging

# Odoo 19 Credentials
URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def inspect_19():
    try:
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL))
        uid = common.authenticate(DB, USER, PASS, {})
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL))
        
        # Check purchase.order fields for invoice links
        po_fields = models.execute_kw(DB, uid, PASS, 'purchase.order', 'fields_get', 
            [], {'attributes': ['string', 'type', 'readonly']})
        
        logger.info("--- Purchase Order Fields related to Invoice ---")
        for f in po_fields:
            if 'invoice' in f:
                logger.info(f"{f}: {po_fields[f]}")

        # Check account.move fields for purchase links
        move_fields = models.execute_kw(DB, uid, PASS, 'account.move', 'fields_get', 
            [], {'attributes': ['string', 'type', 'readonly']})
        
        logger.info("\n--- Account Move Fields related to Purchase ---")
        for f in move_fields:
            if 'purchase' in f:
                logger.info(f"{f}: {move_fields[f]}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    inspect_19()
