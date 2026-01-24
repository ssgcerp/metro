
import xmlrpc.client
import logging

# Odoo 19 Credentials
URL_19 = "https://metro.equdaierp.com"
DB_19 = "metrodb"
USER_19 = "admin"
PASS_19 = "Amaze@321"

# Odoo 14 Credentials
URL_14 = "https://erpmfs.com"
DB_14 = "metro_production_8_8_22"
USER_14 = "Sales.auh@metrofiresystems.com"
PASS_14 = "Sales@185734"

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def diagnose_zeros():
    try:
        common_19 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_19))
        uid_19 = common_19.authenticate(DB_19, USER_19, PASS_19, {})
        models_19 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_19))
        
        common_14 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_14))
        uid_14 = common_14.authenticate(DB_14, USER_14, PASS_14, {})
        models_14 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_14))

        # Context
        companies = models_19.execute_kw(DB_19, uid_19, PASS_19, 'res.company', 'search_read', [[]], {'fields': ['id']})
        CTX = {'allowed_company_ids': [c['id'] for c in companies]}

        # Search Zero POs
        pos_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order', 'search_read', 
            [[('amount_total', '=', 0.0)]], 
            {'fields': ['name', 'state', 'order_line'], 'context': CTX})

        logger.info(f"Remaining Zero POs: {len(pos_19)}")
        
        for po in pos_19[:20]: # Show first 20 details
            name = po['name']
            line_ids_19 = po['order_line']
            
            # Check Odoo 14
            po_14 = models_14.execute_kw(DB_14, uid_14, PASS_14, 'purchase.order', 'search_read', 
                [[('name', '=', name)]], 
                {'fields': ['amount_total', 'order_line'], 'limit': 1})
            
            if not po_14:
                logger.info(f"{name}: Not found in Odoo 14")
                continue
                
            p14 = po_14[0]
            amount_14 = p14['amount_total']
            lines_14_count = len(p14['order_line'])
            lines_19_count = len(line_ids_19)
            
            logger.info(f"{name}: Odoo14 Amount={amount_14}, Lines14={lines_14_count}, Lines19={lines_19_count}")
            
            if amount_14 == 0.0:
                logger.info(f"  -> Original PO also has 0 amount.")
            elif lines_14_count != lines_19_count:
                logger.info(f"  -> Line count mismatch (Skipped by script).")
            elif lines_19_count == 0:
                logger.info(f"  -> No lines in Odoo 19.")
            else:
                 logger.info(f"  -> Should have been fixed? Access issue?")

    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    diagnose_zeros()
