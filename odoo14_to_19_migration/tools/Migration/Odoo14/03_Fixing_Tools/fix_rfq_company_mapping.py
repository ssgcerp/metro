
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

# Mapping: Odoo 14 Branch Name -> Odoo 19 Company Name (or ID)
BRANCH_MAPPING = {
    "FUJAIRAH": "FUJAIRAH",
    "DUBAI": "DUBAI",
    "ABU DHABI": "ABU DHABI",
    "Ras Al Khaimah": "RAS AL KHAIMAH",
    "AJMAN": "AJMAN",
    "DUBAI STORE": "DUBAI STORE",
    "SHARJAH": "SHARJAH"
}

def fix_company_mapping(dry_run=True):
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

        # Pre-fetch Odoo 19 Companies to get IDs
        companies_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'res.company', 'search_read', [[]], {'fields': ['name']})
        company_map_19 = {c['name']: c['id'] for c in companies_19}
        logger.info(f"Odoo 19 Companies: {company_map_19}")

        # Fetch Odoo 19 RFQs (Purchase Orders in ALL states)
        # We need to process 'purchase' and 'done' states as well, as requested by user.
        rfqs_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order', 'search_read', 
            [[]], # Empty domain = fetch all records
            {'fields': ['name', 'company_id']})

        logger.info(f"Checking {len(rfqs_19)} RFQs in Odoo 19...")

        updated_count = 0
        skipped_count = 0 
        failed_count = 0

        for rfq in rfqs_19:
            rfq_name = rfq['name']
            current_company_id = rfq['company_id'][0] if rfq['company_id'] else False
            current_company_name = rfq['company_id'][1] if rfq['company_id'] else "None"

            try:
                # Find matching RFQ in Odoo 14
                rfq_14 = models_14.execute_kw(DB_14, uid_14, PASS_14, 'purchase.order', 'search_read', 
                    [[('name', '=', rfq_name)]], 
                    {'fields': ['branch_id'], 'limit': 1})

                if not rfq_14:
                    # logger.warning(f"RFQ {rfq_name} not found in Odoo 14. Skipping.")
                    skipped_count += 1
                    continue

                branch_data = rfq_14[0].get('branch_id')
                if not branch_data:
                    logger.warning(f"RFQ {rfq_name}: No branch_id in Odoo 14.")
                    skipped_count += 1
                    continue

                branch_name = branch_data[1]
                
                # Determine target company
                target_company_name = BRANCH_MAPPING.get(branch_name)
                # Handle Case Insensitive match if direct lookup fails
                if not target_company_name:
                    for k, v in BRANCH_MAPPING.items():
                        if k.lower() == branch_name.lower():
                            target_company_name = v
                            break
                            
                if not target_company_name:
                     logger.warning(f"RFQ {rfq_name}: Branch '{branch_name}' has no mapping.")
                     skipped_count += 1
                     continue

                target_company_id = company_map_19.get(target_company_name)
                
                if not target_company_id:
                     logger.warning(f"RFQ {rfq_name}: Target company '{target_company_name}' not found in Odoo 19.")
                     skipped_count += 1
                     continue

                # Check if update is needed
                if current_company_id != target_company_id:
                    logger.info(f"RFQ {rfq_name}: Updating Company from '{current_company_name}' to '{target_company_name}'")
                    if not dry_run:
                        models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order', 'write', [[rfq['id']], {'company_id': target_company_id}])
                        # Also update lines? Usually company propagates, but good to check. 
                        # Odoo write on PO usually propagates to lines if in draft.
                        updated_count += 1
                else:
                    # logger.info(f"RFQ {rfq_name}: Company '{current_company_name}' is already correct.")
                    skipped_count += 1

            except Exception as inner_e:
                logger.error(f"Error processing RFQ {rfq_name}: {str(inner_e)}")
                failed_count += 1

        logger.info(f"\n--- Summary ---")
        logger.info(f"Updated: {updated_count}")
        logger.info(f"Skipped/Correct: {skipped_count}")
        logger.info(f"Failed: {failed_count}")
        if dry_run:
            logger.info("NOTE: Dry Run Mode - No changes made.")

    except Exception as e:
        logger.error(f"Global Error: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true', help='Execute updates (disable dry run)')
    args = parser.parse_args()
    
    fix_company_mapping(dry_run=not args.run)
