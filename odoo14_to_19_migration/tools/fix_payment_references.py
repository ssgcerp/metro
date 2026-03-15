import xmlrpc.client
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def main():
    # ── Odoo 18 (Source) ─────────────────────────────────
    src_url  = "https://metro-fire-system-llc.odoo.com"
    src_db   = "metro-fire-system-llc"
    src_user = "sruthi@metrofiresystems.com"
    src_pass = "Sruthi@321"

    # ── Odoo 19 (Destination) ─────────────────────────────
    dst_url  = "https://metro.equdaierp.com"
    dst_db   = "newdb"
    dst_user = "admin"
    dst_pass = "Amaze@321"

    logger.info("Connecting to Odoo 18...")
    s_common = xmlrpc.client.ServerProxy(f"{src_url}/xmlrpc/2/common", allow_none=True)
    s_uid = s_common.authenticate(src_db, src_user, src_pass, {})
    s_models = xmlrpc.client.ServerProxy(f"{src_url}/xmlrpc/2/object", allow_none=True)

    logger.info("Connecting to Odoo 19...")
    d_common = xmlrpc.client.ServerProxy(f"{dst_url}/xmlrpc/2/common", allow_none=True)
    d_uid = d_common.authenticate(dst_db, dst_user, dst_pass, {})
    d_models = xmlrpc.client.ServerProxy(f"{dst_url}/xmlrpc/2/object", allow_none=True)

    # Fetch Odoo 19 vendor bills
    logger.info("Fetching Odoo 19 vendor bills...")
    d_domain = [('move_type', '=', 'in_invoice'), ('name', '!=', False)]
    d_bills = d_models.execute_kw(dst_db, d_uid, dst_pass, 'account.move', 'search_read', [d_domain], {'fields': ['id', 'name', 'payment_reference']})
    logger.info(f"Found {len(d_bills)} bills in Odoo 19.")

    d_bills_map = {b['name']: b for b in d_bills}
    d_names = list(d_bills_map.keys())

    # Fetch Odoo 18 vendor bills matching the names in Odoo 19
    logger.info("Fetching Odoo 18 vendor bills...")
    chunk_size = 500
    s_bills_map = {}
    for i in range(0, len(d_names), chunk_size):
        chunk_names = d_names[i:i+chunk_size]
        s_domain = [('move_type', '=', 'in_invoice'), ('name', 'in', chunk_names)]
        chunk_bills = s_models.execute_kw(src_db, s_uid, src_pass, 'account.move', 'search_read', [s_domain], {'fields': ['name', 'payment_reference']})
        for b in chunk_bills:
            s_bills_map[b['name']] = b
            
    logger.info(f"Found {len(s_bills_map)} matching bills in Odoo 18.")

    updates_made = 0
    errors = 0
    
    # Process combinations
    logger.info("Comparing and updating payment references...")
    for idx, (name, d_bill) in enumerate(d_bills_map.items()):
        if name not in s_bills_map:
            continue
            
        s_bill = s_bills_map[name]
        vals = {}
            
        s_pref = s_bill.get('payment_reference')
        d_pref = d_bill.get('payment_reference')
        
        s_empty = not s_pref
        d_empty = not d_pref
        
        if (s_empty and not d_empty) or (not s_empty and s_pref != d_pref):
            vals['payment_reference'] = s_pref if s_pref else False
            
        if vals:
            try:
                d_models.execute_kw(dst_db, d_uid, dst_pass, 'account.move', 'write', [[d_bill['id']], vals])
                updates_made += 1
                logger.info(f"Updated {name}: {vals}")
            except Exception as e:
                logger.error(f"Error updating {name}: {e}")
                errors += 1
                
        if (idx + 1) % 1000 == 0:
            logger.info(f"Processed {idx + 1}/{len(d_bills_map)} bills...")

    logger.info(f"Finished. Successfully updated: {updates_made} bills. Errors: {errors}.")

if __name__ == '__main__':
    main()
