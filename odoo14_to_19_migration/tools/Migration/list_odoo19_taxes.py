
import xmlrpc.client
import logging

# Odoo 19 Credentials
URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def list_taxes():
    try:
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL))
        uid = common.authenticate(DB, USER, PASS, {})
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL))
        
        # Helper to get Company Name
        def get_company_name(cid):
            if not cid: return "None"
            return models.execute_kw(DB, uid, PASS, 'res.company', 'read', [[cid]], {'fields': ['name']})[0]['name']

        # List taxes
        taxes = models.execute_kw(DB, uid, PASS, 'account.tax', 'search_read', 
            [[]], 
            {'fields': ['name', 'company_id', 'amount']})
            
        logger.info("\n--- Odoo 19 Taxes ---")
        for t in taxes:
            c_id = t['company_id'][0] if t['company_id'] else False
            c_name = t['company_id'][1] if t['company_id'] else "None"
            logger.info(f"ID: {t['id']} | Name: {t['name']} | Company: {c_name} (ID: {c_id}) | Amount: {t['amount']}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    list_taxes()
