
import xmlrpc.client
import sys
import json

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print("STARTING SMART RECONCILIATION AND FIX")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common', allow_none=True)
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
    
    # 1. Fetch Outstanding Bills (In Payment, Partial, Not Paid)
    print("Fetching Outstanding Bills...")
    bill_domain = [('move_type', '=', 'in_invoice'), ('state', '=', 'posted'), ('amount_residual', '>', 0)]
    bills = models.execute_kw(DB, uid, PASS, 'account.move', 'search_read', [bill_domain], {'fields': ['id', 'name', 'amount_total', 'amount_residual', 'partner_id', 'ref', 'company_id']})
    print(f"Found {len(bills)} candidates.")

    # 2. Fetch Unreconciled Payments (and any Debit move lines like Manual Entries)
    print("Fetching Unreconciled Debits...")
    p_line_domain = [
        ('account_type', '=', 'liability_payable'),
        ('reconciled', '=', False),
        ('debit', '>', 0)
    ]
    p_lines = models.execute_kw(DB, uid, PASS, 'account.move.line', 'search_read', [p_line_domain], {'fields': ['id', 'move_id', 'account_id', 'partner_id', 'credit', 'debit', 'amount_residual', 'payment_id', 'company_id']})
    print(f"Found {len(p_lines)} unreconciled debit lines.")

    # Organize by (Partner, Company, Account)
    group_bills = {}
    for b in bills:
        if not b['partner_id'] or not b['company_id']: continue
        # We need to find the bill's payable account. 
        # Actually, let's fetch the lines instead of the moves for bills too?
        # Or just read the payable account from the bill's lines.
        # Speed optimization: search_read lines instead of moves.
        pass

    print("Fetching Bill Payable Lines...")
    b_line_domain = [('move_id.move_type', '=', 'in_invoice'), ('move_id.state', '=', 'posted'), ('account_type', '=', 'liability_payable'), ('reconciled', '=', False)]
    b_lines_all = models.execute_kw(DB, uid, PASS, 'account.move.line', 'search_read', [b_line_domain], {'fields': ['id', 'move_id', 'account_id', 'partner_id', 'amount_residual', 'company_id']})
    
    group_bills = {}
    for bl in b_lines_all:
        if not bl['partner_id'] or not bl['company_id']: continue
        key = (bl['partner_id'][0], bl['company_id'][0], bl['account_id'][0])
        if key not in group_bills: group_bills[key] = []
        group_bills[key].append(bl)

    group_payments = {}
    for pl in p_lines:
        if not pl['partner_id'] or not pl['company_id']: continue
        key = (pl['partner_id'][0], pl['company_id'][0], pl['account_id'][0])
        balance = abs(pl['amount_residual'])
        if key not in group_payments: group_payments[key] = []
        group_payments[key].append({
            'line_id': pl['id'],
            'amount': balance,
            'payment_id': pl['payment_id'][0] if pl['payment_id'] else None
        })

    # 3. Reconciliation Loop
    total_reconciled = 0
    total_sync = 0
    ctx = {'check_move_validity': False, 'check_company': False}

    p_consumed_ids = set()

    for key in group_bills:
        if key not in group_payments: continue
        
        # Sort items: Prioritize FIFO by ID
        b_list = sorted(group_bills[key], key=lambda x: x['id']) 
        p_list = group_payments[key]
        
        # Filter out already consumed globally
        p_list = [p for p in p_list if p['line_id'] not in p_consumed_ids]

        for bl in b_list:
            b_residual = abs(bl['amount_residual'])
            if b_residual <= 0.01: continue
            
            # Find a matching payment (exact amount first)
            match = None
            for p in p_list:
                if p['amount'] <= 0.01: continue
                if abs(p['amount'] - b_residual) < 0.01:
                    match = p
                    break
            
            # Fallback to FIFO
            if not match:
                for p in p_list:
                    if p['amount'] > 0.01:
                        match = p
                        break
            
            if match:
                bl_id = bl['id']
                pl_id = match['line_id']
                
                try:
                    # Direct Reconciliation on move lines
                    all_lines = [int(bl_id), int(pl_id)]
                    print(f"[{total_reconciled+1}] Reconciling Lines {all_lines} (Amt {min(b_residual, match['amount'])})")
                    models.execute_kw(DB, uid, PASS, 'account.move.line', 'reconcile', [all_lines])
                    total_reconciled += 1
                    
                    # Deduct amount
                    consumed = min(b['amount_residual'], match['amount'])
                    b['amount_residual'] -= consumed
                    match['amount'] -= consumed
                    
                    if match['amount'] <= 0.01:
                         p_consumed_ids.add(match['line_id'])
                         # Remove from current p_list too for speed
                         p_list = [p for p in p_list if p['line_id'] != match['line_id']]

                except Exception as e_rec:
                    estr = str(e_rec)
                    if "cannot marshal None" in estr:
                        print("  Reconcile: Marshal error caught (Likely Success).")
                        total_reconciled += 1
                        # Deduct amount (Assume full coverage if match was exact)
                        consumed = min(b['amount_residual'], match['amount'])
                        b['amount_residual'] -= consumed
                        match['amount'] -= consumed
                        if match['amount'] <= 0.01:
                             p_consumed_ids.add(match['line_id'])
                             p_list = [p for p in p_list if p['line_id'] != match['line_id']]
                    else:
                        print(f"  Reconcile Failed: {e_rec}")
                        p_list = [p for p in p_list if p['line_id'] != match['line_id']]
                    continue

                # try:
                #    # Sync ... (omitted for now)
                # except Exception as e_sync:
                #    print(f"  Sync Failed: {e_sync}")

    print(f"\nFinal Summary:")
    print(f"Total Reconciliations: {total_reconciled}")
    print(f"Total Lines Synced: {total_sync}")

if __name__ == "__main__":
    main()
