import xmlrpc.client
import logging

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
    # Target payment that failed
    target_payment_name = "PBFUJ/2025/00005"
    
    try:
        common_18 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_18), allow_none=True)
        uid_18 = common_18.authenticate(DB_18, USER_18, PASS_18, {})
        models_18 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_18), allow_none=True)

        logger.info("Connected to Odoo 18.")
        
        # Fetch inbound customer payments
        payments_18 = models_18.execute_kw(DB_18, uid_18, PASS_18, 'account.payment', 'search_read', 
            [[('name', '=', target_payment_name)]], 
            {'fields': ['name', 'amount', 'currency_id', 'date', 'state', 'journal_id', 'payment_method_line_id', 'reconciled_invoice_ids', 'partner_id'], 'limit': 1})
            
        p_18 = payments_18[0]
        logger.info(f"Odoo 18 Payment structure: {p_18}")
        
        common_19 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_19), allow_none=True)
        uid_19 = common_19.authenticate(DB_19, USER_19, PASS_19, {})
        models_19 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_19), allow_none=True)

        logger.info("Connected to Odoo 19.")
        
        journal_18 = p_18['journal_id']
        j_name = journal_18[1]
        j_domain = [('name', '=', j_name), ('type', 'in', ['bank', 'cash'])]
        j_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.journal', 'search_read', 
            [j_domain], {'fields': ['id', 'name', 'default_account_id'], 'limit': 1})
            
        journal_id_19 = j_19[0]['id']
        
        partner_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'res.partner', 'search', 
            [[('name', '=', p_18['partner_id'][1])]], {'limit': 1})
        partner_id_19 = partner_19[0]

        pml_method = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.payment.method.line', 'search_read', 
            [[('payment_type', '=', 'inbound'), ('journal_id', '=', journal_id_19), ('code', '=', 'manual')]], 
            {'fields': ['id'], 'limit': 1})
        pml_id_19 = pml_method[0]['id']
        
        payment_vals = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': partner_id_19,
            'amount': p_18['amount'],
            'date': p_18['date'],
            'journal_id': journal_id_19,
            'payment_method_line_id': pml_id_19,
            'payment_reference': f"Migrated from {p_18['name']}",
        }
        
        print("\nDictionary to send to Odoo 19:")
        print(payment_vals)
        print("Data types:")
        for k, v in payment_vals.items():
            print(f"{k}: {type(v)}")

        payment_vals = {k: v for k, v in payment_vals.items() if v is not None}
        
        print("\nCleaned dictionary:")
        print(payment_vals)
        
        try:
            # Let's see if we can do an empty create call or simulate the failure
            models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.payment', 'create', [payment_vals])
            print("Successfully explicitly pushed record!")
        except Exception as e:
            print(f"FAILED TO PUSH EXPLICITLY: {e}")

    except Exception as e:
        logger.error(f"Global Error: {str(e)}")

if __name__ == "__main__":
    debug_payments()
