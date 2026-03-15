import xmlrpc.client
import logging
import argparse

# Odoo 19 Credentials
URL_19 = "https://metro.equdaierp.com"
DB_19 = "newdb"
USER_19 = "admin"
PASS_19 = "Amaze@321"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def delete_customer_payments():
    try:
        common_19 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_19))
        uid_19 = common_19.authenticate(DB_19, USER_19, PASS_19, {})
        models_19 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_19))

        logger.info("Connected to Odoo 19.")

        # Find all customer payments
        domain = [('payment_type', '=', 'inbound'), ('partner_type', '=', 'customer')]
        payments = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.payment', 'search_read', 
            [domain], {'fields': ['id', 'state', 'move_id']})

        if not payments:
            logger.info("No customer payments found in Odoo 19.")
            return

        logger.info(f"Found {len(payments)} customer payments to delete.")

        # Step 1: Remove payment to invoice reconciliation (unreconcile)
        # We need to find the move lines and remove reconciliation so we can cancel
        payment_ids = [p['id'] for p in payments]
        move_ids = [p['move_id'][0] for p in payments if p.get('move_id')]
        
        if move_ids:
            # Find the move lines for these moves
            lines = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move.line', 'search_read', 
                [[('move_id', 'in', move_ids)]], {'fields': ['id', 'reconciled']})
            line_ids = [line['id'] for line in lines]
            if line_ids:
                logger.info(f"Removing reconciliations for {len(line_ids)} move lines...")
                try:
                    models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.move.line', 'remove_move_reconcile', [line_ids])
                except Exception as e:
                    logger.warning(f"Could not remove reconciliation, might not be needed: {e}")

        # Step 2: Cancel payments
        # Some payments might be posted. Action reset to draft or cancel.
        logger.info("Canceling payments...")
        try:
            models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.payment', 'action_cancel', [payment_ids])
        except Exception as err:
            if "cannot marshal None unless allow_none is enabled" in str(err):
                logger.info("Payments canceled (ignored None return).")
            else:
                raise err
        
        # Step 3: Unlink (Delete) payments
        # In Odoo, deleting a payment usually deletes the underlying account.move if it is canceled/draft.
        logger.info("Unlinking payments...")
        try:
            models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.payment', 'unlink', [payment_ids])
        except Exception as err:
            if "cannot marshal None unless allow_none is enabled" in str(err):
                logger.info("Payments unlinked (ignored None return).")
            else:
                raise err
        
        logger.info("Successfully deleted customer payments and their associated journal entries.")

    except Exception as e:
        logger.error(f"Error during deletion: {str(e)}")

if __name__ == "__main__":
    delete_customer_payments()
