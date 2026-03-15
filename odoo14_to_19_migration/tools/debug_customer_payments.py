import xmlrpc.client
import logging
import json

URL_19 = "https://metro.equdaierp.com"
DB_19 = "newdb"
USER_19 = "admin"
PASS_19 = "Amaze@321"

URL_18 = "https://metro-fire-system-llc.odoo.com"
DB_18 = "metro-fire-system-llc"
USER_18 = "sruthi@metrofiresystems.com"
PASS_18 = "Sruthi@321"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_payments():
    try:
        common_18 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_18), allow_none=True)
        uid_18 = common_18.authenticate(DB_18, USER_18, PASS_18, {})
        models_18 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_18), allow_none=True)

        logger.info("Connected to Odoo 18.")
        
        # Search for any inbound customer payment in Odoo 18
        payments_18 = models_18.execute_kw(DB_18, uid_18, PASS_18, 'account.payment', 'search_read', 
            [[('payment_type', '=', 'inbound'), ('partner_type', '=', 'customer')]], 
            {'fields': ['name', 'amount', 'currency_id', 'date', 'state', 'journal_id', 'payment_method_line_id', 'reconciled_invoice_ids', 'partner_id'], 'limit': 3})
            
        logger.info(f"Odoo 18 Payments found: {len(payments_18)}")
        for p in payments_18:
            print("Odoo 18 Payment structure:")
            print(json.dumps(p, indent=2, default=str))
            
            # Fetch invoice details for the reconciled invoices
            if p.get('reconciled_invoice_ids'):
                invs = models_18.execute_kw(DB_18, uid_18, PASS_18, 'account.move', 'read', 
                    [p['reconciled_invoice_ids']], {'fields': ['name', 'amount_total', 'partner_id', 'state']})
                print("Reconciled Invoices:")
                print(json.dumps(invs, indent=2, default=str))

    except Exception as e:
        logger.error(f"Global Error: {str(e)}")

if __name__ == "__main__":
    debug_payments()
