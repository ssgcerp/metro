
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

MASTER_COMPANY_ID = 1 # ABU DHABI

def main():
    print(f"STARTING GLOBAL PARTNER RECONCILIATION (Unifying to Company {MASTER_COMPANY_ID})")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
    
    # 1. Get Master Account for Company 1
    master_acc = models.execute_kw(DB, uid, PASS, 'account.account', 'search', [[('code', '=', '201002'), ('company_ids', 'in', [MASTER_COMPANY_ID])]])
    if not master_acc:
        print("Error: Could not find account 201002 for Company 1")
        return
    master_acc_id = master_acc[0]
    print(f"Master Account ID: {master_acc_id}")

    # 2. Fetch ALL unreconciled payable lines across ALL companies
    print("Fetching all unreconciled payable lines...")
    domain = [('account_type', '=', 'liability_payable'), ('reconciled', '=', False)]
    lines = models.execute_kw(DB, uid, PASS, 'account.move.line', 'search_read', [domain], {'fields': ['id', 'partner_id', 'company_id', 'debit', 'credit', 'amount_residual', 'account_id']})
    print(f"Found {len(lines)} lines.")

    # 3. Group by Partner
    partner_groups = {}
    for l in lines:
        if not l['partner_id']: continue
        pid = l['partner_id'][0]
        if pid not in partner_groups: partner_groups[pid] = []
        partner_groups[pid].append(l)

    # 4. Process each partner
    total_moved = 0
    total_reconciled = 0
    ctx = {'check_move_validity': False, 'check_company': False}

    for pid, l_list in partner_groups.items():
        # Check if they have both debits and credits
        debit_lines = [l for l in l_list if l['debit'] > 0]
        credit_lines = [l for l in l_list if l['credit'] > 0]
        
        if not debit_lines or not credit_lines:
            continue
            
        print(f"Partner {pid} ({l_list[0]['partner_id'][1]}): {len(debit_lines)} Debits, {len(credit_lines)} Credits")
        
        # Move all to Master Company and Master Account
        to_move = []
        for l in l_list:
            if l['company_id'][0] != MASTER_COMPANY_ID or l['account_id'][0] != master_acc_id:
                to_move.append(l['id'])
        
        if to_move:
            print(f"  Moving {len(to_move)} lines to Company {MASTER_COMPANY_ID} Acc {master_acc_id}...")
            try:
                models.execute_kw(DB, uid, PASS, 'account.move.line', 'write', [to_move, {'company_id': MASTER_COMPANY_ID, 'account_id': master_acc_id}], {'context': ctx})
                total_moved += len(to_move)
            except Exception as e:
                print(f"  Move Failed: {e}")
                continue

        # Recompute local list (assume move succeeded for logic)
        for l in l_list:
            l['company_id'] = [MASTER_COMPANY_ID]
            l['account_id'] = [master_acc_id]

        # FIFO Reconcile
        d_list = sorted(debit_lines, key=lambda x: x['id'])
        c_list = sorted(credit_lines, key=lambda x: x['id'])
        
        for c in c_list:
            c_res = abs(c['amount_residual'])
            if c_res <= 0.01: continue
            
            for d in d_list:
                d_res = abs(d['amount_residual'])
                if d_res <= 0.01: continue
                
                try:
                    print(f"    Reconciling {c['id']} with {d['id']}...")
                    models.execute_kw(DB, uid, PASS, 'account.move.line', 'reconcile', [[c['id'], d['id']]])
                    total_reconciled += 1
                    
                    consumed = min(c_res, d_res)
                    c['amount_residual'] = c_res - consumed
                    d['amount_residual'] = d_res - consumed
                    c_res -= consumed
                    if c_res <= 0.01: break
                except Exception as e:
                    if "cannot marshal None" in str(e):
                        total_reconciled += 1
                    else:
                        print(f"      Reconcile Failed: {e}")
                    break

    print(f"\nFinal Summary:")
    print(f"Total Lines Moved to Master Company: {total_moved}")
    print(f"Total Reconciliations: {total_reconciled}")

if __name__ == "__main__":
    main()
