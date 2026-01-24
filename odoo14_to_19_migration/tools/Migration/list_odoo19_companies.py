
import xmlrpc.client
import logging

# Odoo 19 Credentials
URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def list_companies():
    try:
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL))
        uid = common.authenticate(DB, USER, PASS, {})
        
        if not uid:
            logger.error("Authentication failed")
            return

        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL))
        
        companies = models.execute_kw(DB, uid, PASS, 'res.company', 'search_read', 
            [[]], 
            {'fields': ['name']})
            
        logger.info("\n--- Companies in Odoo 19 ---")
        for company in companies:
            logger.info(f"ID: {company['id']}, Name: {company['name']}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    list_companies()
