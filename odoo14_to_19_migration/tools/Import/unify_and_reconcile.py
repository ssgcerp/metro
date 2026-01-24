
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print("STARTING ACCOUNT UNIFICATION AND RECONCILE")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
    
    # 1. Map each company to its "Master" Payable Account
    print("Detecting Master Payable Accounts...")
    # Typically code '201002'
    acc_ids = models.execute_kw(DB, uid, PASS, 'account.account', 'search_read', [[('code', '=', '201002')]], {'fields': ['id', 'company_ids']})
    company_master_acc = {}
    for a in acc_ids:
        for cid in a['company_ids']:
            company_master_acc[cid] = a['id']
    
    print(f"Master Accounts: {company_master_acc}")

    # 2. Find all unreconciled lines on any Payable account
    print("Fetching all unreconciled payable lines...")
    domain = [('account_type', '=', 'liability_payable'), ('reconciled', '=', False)]
    # Use search in batches if too many
    lines = models.execute_kw(DB, uid, PASS, 'account.move.line', 'search_read', [domain], {'fields': ['id', 'account_id', 'partner_id', 'company_id', 'debit', 'credit', 'amount_residual']})
    print(f"Found {len(lines)} lines.")

    # 3. Group by (Partner, Company)
    groups = {}
    for l in lines:
        if not l['partner_id'] or not l['company_id']: continue
        key = (l['partner_id'][0], l['company_id'][0])
        if key not in groups: groups[key] = []
        groups[key].append(l)

    # 4. Process Groups
    total_unified = 0
    total_reconciled = 0
    ctx = {'check_move_validity': False, 'check_company': False}

    for key, l_list in groups.items():
        pid, cid = key
        target_acc = company_master_acc.get(cid)
        if not target_acc:
             # Fallback: if no 201002, pick the one with most lines? or skip
             continue
        
        # Check if unification is needed
        needs_unify = False
        for l in l_list:
            if l['account_id'][0] != target_acc:
                needs_unify = True
                break
        
        if needs_unify:
            print(f"Partner {pid} Company {cid}: Unifying {len(l_list)} lines to Acc {target_acc}...")
            to_update = [l['id'] for l in l_list if l['account_id'][0] != target_acc]
            try:
                models.execute_kw(DB, uid, PASS, 'account.move.line', 'write', [to_update, {'account_id': target_acc}], {'context': ctx})
                total_unified += len(to_update)
                # Refresh local account_id
                for l in l_list: l['account_id'] = [target_acc]
            except Exception as e:
                print(f"  Unify Failed for {pid}: {e}")
                continue

        # 5. FIFO Reconcile within this partner/company/account
        debits = sorted([l for l in l_list if l['debit'] > 0], key=lambda x: x['id'])
        credits = sorted([l for l in l_list if l['credit'] > 0], key=lambda x: x['id'])
        
        for c in credits:
            c_res = abs(c['amount_residual'])
            if c_res <= 0.01: continue
            
            for d in debits:
                d_res = abs(d['amount_residual'])
                if d_res <= 0.01: continue
                
                # Reconcile
                print(f"  Reconciling Bill Line {c['id']} with Debit Line {d['id']}...")
                try:
                    models.execute_kw(DB, uid, PASS, 'account.move.line', 'reconcile', [[c['id'], d['id']]])
                    total_reconciled += 1
                    
                    # Update local residual
                    consumed = min(c_res, d_res)
                    c['amount_residual'] = c_res - consumed # simplified
                    d['amount_residual'] = d_res - consumed
                    c_res -= consumed
                    if c_res <= 0.01: break
                except Exception as e:
                    # Likely marshal error or already reconciled
                    if "cannot marshal None" in str(e):
                         total_reconciled += 1
                    else:
                         print(f"    Reconcile Failed: {e}")
                    # Assume consumed for local tracking if exact match or similar
                    break

    print(f"\nSummary:")
    print(f"Total Lines Unified: {total_unified}")
    print(f"Total Reconciliations: {total_reconciled}")

if __name__ == "__main__":
    main()
