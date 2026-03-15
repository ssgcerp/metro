import xmlrpc.client
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def main():
    # Odoo 18
    url_18 = "https://metro-fire-system-llc.odoo.com"
    db_18 = "metro-fire-system-llc"
    username_18 = "sruthi@metrofiresystems.com"
    password_18 = "Sruthi@321"

    # Odoo 19
    url_19 = "https://metro.equdaierp.com"
    db_19 = "newdb"
    username_19 = "admin"
    password_19 = "Amaze@321"

    logger.info("Connecting to Odoo 18...")
    s_common = xmlrpc.client.ServerProxy(f"{url_18}/xmlrpc/2/common", allow_none=True)
    s_uid = s_common.authenticate(db_18, username_18, password_18, {})
    s_models = xmlrpc.client.ServerProxy(f"{url_18}/xmlrpc/2/object", allow_none=True)

    logger.info("Connecting to Odoo 19...")
    d_common = xmlrpc.client.ServerProxy(f"{url_19}/xmlrpc/2/common", allow_none=True)
    d_uid = d_common.authenticate(db_19, username_19, password_19, {})
    d_models = xmlrpc.client.ServerProxy(f"{url_19}/xmlrpc/2/object", allow_none=True)

    logger.info("Fetching Odoo 18 out_invoices...")
    inv_18 = s_models.execute_kw(db_18, s_uid, password_18, 'account.move', 'search_read', 
                                 [[('move_type', '=', 'out_invoice')]], {'fields': ['name']})
    
    logger.info("Fetching Odoo 19 out_invoices...")
    inv_19 = d_models.execute_kw(db_19, d_uid, password_19, 'account.move', 'search_read', 
                                 [[('move_type', '=', 'out_invoice')]], {'fields': ['name']})

    names_18 = {i['name'] for i in inv_18 if i.get('name')}
    names_19 = {i['name'] for i in inv_19 if i.get('name')}

    missing = names_18 - names_19

    logger.info("-" * 50)
    logger.info(f"Missing Customer Invoices in Odoo 19 (Count: {len(missing)}):")
    logger.info("-" * 50)
    for name in sorted(missing):
        logger.info(f"{name}")
    logger.info("-" * 50)

if __name__ == "__main__":
    main()
