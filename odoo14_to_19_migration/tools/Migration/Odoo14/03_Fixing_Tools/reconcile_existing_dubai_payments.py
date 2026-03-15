import xmlrpc.client
import ssl
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
_logger = logging.getLogger(__name__)

# Configuration
URL = 'https://metro.equdaierp.com'
DB = 'newdb'
USER = 'admin'
PWD = 'Amaze@321'
COMPANY_NAME = 'DUBAI'

def get_odoo_client(url, db, user, pwd):
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context(), allow_none=True)
    uid = common.authenticate(db, user, pwd, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context(), allow_none=True)
    return uid, models

def reconcile_payment_to_invoice(models, db, uid, pwd, payment_id, partner_id, dest_company_id):
    try:
        payment = models.execute_kw(db, uid, pwd, 'account.payment', 'read', [[payment_id], ['move_id', 'name', 'memo']])
        if not payment: return False
        
        move_field = payment[0].get('move_id')
        if not move_field: return False
        move_id = move_field[0]

        # Get the receivable line of the payment
        pay_lines = models.execute_kw(db, uid, pwd, 'account.move.line', 'search_read', 
            [[('move_id', '=', move_id), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]],
            {'fields': ['id', 'credit']}
        )
        if not pay_lines: return False
        
        raw_memo = payment[0].get('memo')
        if not raw_memo: return False
        
        # Support comma-separated memos
        memo_parts = [m.strip() for m in str(raw_memo).split(',')]
        reconciled_any = False

        for memo in memo_parts:
            if not memo: continue
            
            # Find invoice by number (exact or ends with)
            inv_domain = [
                ('move_type', '=', 'out_invoice'), 
                ('state', '=', 'posted'), 
                ('payment_state', 'in', ['not_paid', 'partial']), 
                '|', ('name', '=', memo), ('name', '=ilike', '%' + memo)
            ]
            if partner_id:
                inv_domain.insert(0, ('partner_id', '=', partner_id))
            
            invs = models.execute_kw(db, uid, pwd, 'account.move', 'search_read', [inv_domain], {'fields': ['id', 'name']})
            
            if invs:
                target_inv = invs[0]
                inv_id = target_inv['id']
                
                # Get the receivable line of the invoice
                inv_lines = models.execute_kw(db, uid, pwd, 'account.move.line', 'search_read', 
                    [[('move_id', '=', inv_id), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]],
                    {'fields': ['id']}
                )
                
                if inv_lines:
                    try:
                        # Reconcile payment line with invoice line
                        models.execute_kw(db, uid, pwd, 'account.move.line', 'reconcile', [[pay_lines[0]['id'], inv_lines[0]['id']]])
                        _logger.info(f"    Reconciled {payment[0]['name']} with {target_inv['name']}")
                        reconciled_any = True
                    except Exception as e:
                        if "marshal None" not in str(e):
                            _logger.warning(f"    Failed to reconcile: {e}")
        return reconciled_any
    except Exception as e:
        _logger.error(f"  Error in reconciliation logic: {e}")
        return False

def mark_payment_as_cleared(models, db, uid, pwd, payment_id):
    try:
        pay_data = models.execute_kw(db, uid, pwd, 'account.payment', 'read', [[payment_id], ['move_id', 'journal_id', 'date', 'amount', 'currency_id', 'name']])
        if not pay_data: return

        move_id = pay_data[0]['move_id'][0] if pay_data[0].get('move_id') else False
        journal_id = pay_data[0]['journal_id'][0] if pay_data[0].get('journal_id') else False
        payment_date = pay_data[0]['date']
        amount = pay_data[0]['amount']
        curr_field = pay_data[0].get('currency_id')
        currency_id = curr_field[0] if curr_field else False
        payment_name = pay_data[0].get('name')

        if not move_id or not journal_id: return

        # Find liquidity line (usually credit for inbound payment)
        lines = models.execute_kw(db, uid, pwd, 'account.move.line', 'search_read', 
            [[('move_id', '=', move_id), ('reconciled', '=', False), ('account_id.account_type', '!=', 'asset_receivable'), ('account_id.account_type', '!=', 'liability_payable')]],
            {'fields': ['id', 'account_id', 'debit', 'credit', 'name']}
        )
        if not lines: return

        liquidity_line = lines[0]
        outstanding_account_id = liquidity_line['account_id'][0]
        
        journal_data = models.execute_kw(db, uid, pwd, 'account.journal', 'read', [[journal_id], ['default_account_id']])
        if not journal_data or not journal_data[0]['default_account_id']: return
        bank_account_id = journal_data[0]['default_account_id'][0]
        
        if bank_account_id == outstanding_account_id: return

        # Create clearance entry
        clearance_move_vals = {
            'journal_id': journal_id,
            'date': payment_date,
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {
                    'account_id': bank_account_id,
                    'name': f"Bank Clearance - {payment_name}",
                    'debit': amount,
                    'credit': 0.0,
                    'currency_id': currency_id,
                }),
                (0, 0, {
                    'account_id': outstanding_account_id,
                    'name': f"Clearance - {payment_name}",
                    'debit': 0.0,
                    'credit': amount,
                    'currency_id': currency_id,
                })
            ]
        }
        
        clearance_move_id = models.execute_kw(db, uid, pwd, 'account.move', 'create', [clearance_move_vals])
        models.execute_kw(db, uid, pwd, 'account.move', 'action_post', [[clearance_move_id]])
        
        clearance_lines = models.execute_kw(db, uid, pwd, 'account.move.line', 'search_read', 
            [[('move_id', '=', clearance_move_id), ('account_id', '=', outstanding_account_id)]],
            {'fields': ['id']}
        )
        if clearance_lines:
            models.execute_kw(db, uid, pwd, 'account.move.line', 'reconcile', [[liquidity_line['id'], clearance_lines[0]['id']]])
            _logger.info(f"    Payment marked as fully PAID (cleared with bank).")
    except Exception as e:
        if "marshal None" not in str(e):
            _logger.warning(f"  Failed to mark as Paid: {e}")

def main():
    uid, models = get_odoo_client(URL, DB, USER, PWD)
    if not uid:
        print("Authentication failed.")
        return

    company_id = models.execute_kw(DB, uid, PWD, 'res.company', 'search', [[('name', '=', COMPANY_NAME)]])[0]
    
    # Get all posted payments (to reconcile them)
    domain = [
        ('company_id', '=', company_id),
        ('partner_type', '=', 'customer'),
        ('payment_type', '=', 'inbound'),
        ('state', '=', 'in_process'),   # Odoo 19 uses in_process for posted but unreconciled
        ('is_reconciled', '=', False) # Only unreconciled ones
    ]
    
    pays = models.execute_kw(DB, uid, PWD, 'account.payment', 'search_read', [domain], {'fields': ['id', 'name', 'partner_id']})
    print(f"Found {len(pays)} unreconciled posted payments for DUBAI.")

    for i, p in enumerate(pays):
        print(f"Processing ({i+1}/{len(pays)}): {p['name']}")
        partner_id = p['partner_id'][0] if p['partner_id'] else False
        
        # 1. Reconcile to Invoice
        reconciled = reconcile_payment_to_invoice(models, DB, uid, PWD, p['id'], partner_id, company_id)
        
        # 2. Mark as PAID (Cleared) if reconciled or if we just want it to be PAID
        # Usually we mark it as cleared if it's already posted
        mark_payment_as_cleared(models, DB, uid, PWD, p['id'])

    print("\nReconciliation process finished.")

if __name__ == "__main__":
    main()
