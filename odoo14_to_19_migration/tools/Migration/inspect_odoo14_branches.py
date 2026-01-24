
import xmlrpc.client
import logging
import sys

# Odoo 14 Credentials (Retrieved)
URL = "https://erpmfs.com"
DB = "metro_production_8_8_22"
USER = "Sales.auh@metrofiresystems.com"
PASS = "Sales@185734"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def inspect_branches():
    try:
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL))
        uid = common.authenticate(DB, USER, PASS, {})
        
        if not uid:
            logger.error("Authentication failed")
            return

        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL))
        
        # 1. Find Branch field in purchase.order
        fields = models.execute_kw(DB, uid, PASS, 'purchase.order', 'fields_get', [], {'attributes': ['string', 'type', 'relation']})
        
        branch_field = None
        logger.info("--- Searching for Branch fields in purchase.order ---")
        for field_name, field_data in fields.items():
            if 'branch' in field_name.lower() or 'branch' in field_data.get('string', '').lower():
                logger.info(f"Found candidate: {field_name} ({field_data.get('string')}) - Type: {field_data.get('type')}")
                if not branch_field:
                    branch_field = field_name

        if not branch_field:
            logger.warning("No explicit 'branch' field found. Checking 'company_id' or others as fallback.")
            # Maybe it is company_id in Odoo 14 that represents branch?
            branch_field = 'company_id' # Fallback to check
            
        logger.info(f"Using field '{branch_field}' for analysis.")

        # 2. Fetch unique values
        rfqs = models.execute_kw(DB, uid, PASS, 'purchase.order', 'search_read', 
            [[]], 
            {'fields': [branch_field], 'limit': 100})
            
        branches = {}
        for rfq in rfqs:
            val = rfq.get(branch_field)
            if val:
                # Many2one returns [id, name], selection/char returns value
                if isinstance(val, list):
                    branches[val[0]] = val[1]
                else:
                    branches[val] = str(val)
        
        logger.info("\n--- Distinct Branches / Companies in Odoo 14 ---")
        for b_id, b_name in branches.items():
            logger.info(f"ID: {b_id}, Name: {b_name}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    inspect_branches()
