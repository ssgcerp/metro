
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

def link_bills(dry_run=True):
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

        # Fetch Odoo 19 POs
        rfqs_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'purchase.order', 'search_read', 
            [[]], 
            {'fields': ['name', 'invoice_ids']})

        logger.info(f"Checking {len(rfqs_19)} POs in Odoo 19...")

        found_count = 0
        linked_count = 0
        skipped_count = 0
        failed_count = 0
        
        logger.info(f"Starting execution. Dry Run: {dry_run}")

        for po in rfqs_19:
            po_name = po['name']
            po_id_19 = po['id']

            try:
                # Find PO in Odoo 14
                po_14 = models_14.execute_kw(DB_14, uid_14, PASS_14, 'purchase.order', 'search_read', 
                    [[('name', '=', po_name)]], 
                    {'fields': ['invoice_ids'], 'limit': 1})

                if not po_14 or not po_14[0]['invoice_ids']:
                    skipped_count += 1
                    continue

                inv_ids_14 = po_14[0]['invoice_ids']
                
                # Fetch Bill Details from 14
                invoices_14 = models_14.execute_kw(DB_14, uid_14, PASS_14, 'account.move', 'read', 
                    [inv_ids_14], 
                    {'fields': ['name', 'ref', 'state', 'move_type']})

                for inv in invoices_14:
                    if inv['move_type'] != 'in_invoice':
                        continue
                    
                    if inv['state'] != 'posted':
                        continue
                        
                    bill_name = inv['name'] # e.g. BILL/2023/001
                    if not bill_name or bill_name == '/':
                         continue

                    bill_ref = inv['ref']

                    # Find Bill in Odoo 19 by Name
                    bill_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'search_read', 
                        [[('name', '=', bill_name), ('move_type', '=', 'in_invoice')]], 
                        {'fields': ['id', 'purchase_id', 'invoice_origin'], 'limit': 1})

                    # Fallback: Find by Ref
                    if not bill_19 and bill_ref:
                         bill_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'search_read', 
                            [[('ref', '=', bill_ref), ('move_type', '=', 'in_invoice')]], 
                            {'fields': ['id', 'purchase_id', 'invoice_origin'], 'limit': 1})

                    if bill_19:
                        b_19 = bill_19[0]
                        bill_id_19 = b_19['id']
                        current_purchase_id = b_19['purchase_id'][0] if b_19['purchase_id'] else False
                        
                        if current_purchase_id != po_id_19:
                            found_count += 1
                            logger.info(f"Linking PO {po_name} to Bill {bill_name} (ID: {bill_id_19})")
                            
                            vals = {'purchase_id': po_id_19}
                            if not b_19['invoice_origin']:
                                vals['invoice_origin'] = po_name
                            elif po_name not in b_19['invoice_origin']:
                                vals['invoice_origin'] = b_19['invoice_origin'] + ", " + po_name

                            if not dry_run:
                                models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move', 'write', [[bill_id_19], vals])
                                linked_count += 1
                        else:
                            # Already linked
                            pass
                    else:
                        logger.warning(f"Bill {bill_name} (Ref: {bill_ref}) from PO {po_name} NOT found in Odoo 19.")
                        skipped_count += 1 

            except Exception as inner_e:
                logger.error(f"Error processing PO {po_name}: {str(inner_e)}")
                failed_count += 1

        logger.info(f"\n--- Summary ---")
        logger.info(f"Found Matches: {found_count}")
        logger.info(f"Actually Linked: {linked_count}")
        logger.info(f"skipped/Missing/Already Linked: {skipped_count}")
        logger.info(f"Failed: {failed_count}")
        if dry_run:
            logger.info("NOTE: Dry Run Mode - No changes made.")

    except Exception as e:
        logger.error(f"Global Error: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true', help='Execute updates (disable dry run)')
    args = parser.parse_args()
    
    print(f"Arguments: {args}")
    link_bills(dry_run=not args.run)
