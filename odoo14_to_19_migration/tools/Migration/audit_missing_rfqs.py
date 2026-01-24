
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

def audit_missing_rfqs():
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

        # Fetch Odoo 19 PO Names
        logger.info("Fetching Odoo 19 PO names...")
        rfqs_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order', 'search_read', 
            [[]], 
            {'fields': ['name']})
        odoo19_names = set(r['name'] for r in rfqs_19)
        logger.info(f"Odoo 19 Total POs: {len(odoo19_names)}")

        # Fetch Odoo 14 PO Names
        logger.info("Fetching Odoo 14 PO names...")
        # We might want to filter relevant ones? Or get all. Let's get all.
        rfqs_14 = models_14.execute_kw(DB_14, uid_14, PASS_14, 'purchase.order', 'search_read', 
            [[]], 
            {'fields': ['name']})
        odoo14_names = set(r['name'] for r in rfqs_14)
        logger.info(f"Odoo 14 Total POs: {len(odoo14_names)}")

        # Calculate Difference
        missing_in_19 = odoo14_names - odoo19_names
        
        logger.info("\n--- Missing RFQs in Odoo 19 (Present in 14) ---")
        logger.info(f"Count: {len(missing_in_19)}")
        
        # Sort and print
        sorted_missing = sorted(list(missing_in_19))
        for name in sorted_missing:
            # Maybe print only ID or Name?
            print(name)
            
    except Exception as e:
        logger.error(f"Global Error: {str(e)}")

if __name__ == "__main__":
    audit_missing_rfqs()
