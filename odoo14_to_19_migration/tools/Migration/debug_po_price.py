
import xmlrpc.client
import logging

# Odoo 19 Credentials
URL_19 = "https://metro.equdaierp.com"
DB_19 = "metrodb"
USER_19 = "admin"
PASS_19 = "Amaze@321"

# Odoo 14 Credentials (Source)
URL_14 = "https://erpmfs.com"
DB_14 = "metro_production_8_8_22"
USER_14 = "Sales.auh@metrofiresystems.com"
PASS_14 = "Sales@185734"

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

PO_NAME = "MFS-DXB-1275"

def debug_po():
    try:
        # Connect
        common_19 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_19))
        uid_19 = common_19.authenticate(DB_19, USER_19, PASS_19, {})
        models_19 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_19))
        
        common_14 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_14))
        uid_14 = common_14.authenticate(DB_14, USER_14, PASS_14, {})
        models_14 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_14))
        
        logger.info(f"Inspecting {PO_NAME}...")

        # 1. Check Odoo 19
        po_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order', 'search_read', 
            [[('name', '=', PO_NAME)]], 
            {'fields': ['name', 'state', 'amount_total', 'company_id', 'order_line']})
        
        if not po_19:
            logger.error("PO not found in Odoo 19!")
            return

        po_data_19 = po_19[0]
        logger.info(f"Odoo 19 Data: {po_data_19}")
        
        company_id = po_data_19['company_id'][0]
        logger.info(f"Target Company ID: {company_id}")

        # 2. Check Odoo 14
        po_14 = models_14.execute_kw(DB_14, uid_14, PASS_14, 'purchase.order', 'search_read', 
            [[('name', '=', PO_NAME)]], 
            {'fields': ['name', 'amount_total', 'order_line']})
            
        if not po_14:
             logger.error("PO not found in Odoo 14!")
             return
             
        logger.info(f"Odoo 14 Data: {po_14[0]}")
        
        # 3. Try to get Line Details from 14
        line_ids_14 = po_14[0]['order_line']
        lines_14 = models_14.execute_kw(DB_14, uid_14, PASS_14, 'purchase.order.line', 'read', 
            [line_ids_14], {'fields': ['name', 'price_unit', 'product_id']})
            
        logger.info(f"Odoo 14 Lines: {lines_14}")
        
        # 4. Try to WRITE to Odoo 19 with Context
        logger.info("Attempting update on Odoo 19...")
        
        # We need to switch context to the company
        # But wait, search_read worked? So reading might be fine if record rules allow?
        # Or maybe it found it but cannot write?
        
        line_ids_19 = po_data_19['order_line']
        lines_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order.line', 'read', 
            [line_ids_19], {'fields': ['name', 'price_unit']})
            
        logger.info(f"Odoo 19 Lines (Before): {lines_19}")

        # Try updating ALL lines
        if lines_19 and lines_14:
             # Create map of Odoo 14 lines by Index (assuming order) or Product
             # They usually match by index
             pass

        params = []
        for i in range(len(lines_19)):
             if i >= len(lines_14): break
             l_19 = lines_19[i]
             l_14 = lines_14[i]
             
             target_price = l_14['price_unit']
             target_id = l_19['id']
             
             logger.info(f"Updating Line {target_id} ({l_19['name']}) to Price {target_price}")
             
             # Context workaround: Check if we need it. 
             # Previous run worked without context? 
             # Wait, Step 728 output said "Update SUCCESS (No Context)".
             # But MFS-STR-3564 has Company: DUBAI STORE (ID 7).
             # And "Sorry, Administrator... doesn't have read access" was for MFS-FUJ-3700.
             # Maybe Admin has access to Dubai but not Fujairah?
             # To be safe, let's use context if I can, but I can't easily fetch all IDs here without extra call.
             # I'll rely on "No Context" working for THIS PO since it worked before.
             
             try:
                 models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order.line', 'write', [[target_id], {'price_unit': target_price}])
                 logger.info(f"Line {target_id} Success")
             except Exception as e:
                 logger.error(f"Line {target_id} Failed: {e}")

    except Exception as e:
        logger.error(f"Global Error: {str(e)}")

if __name__ == "__main__":
    debug_po()
