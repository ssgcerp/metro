
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print("STARTING ROBUST GLOBAL NETTING AND UNIFICATION")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
    
    # 1. Map each company to its Master Payable and Master Suspense Accounts
    print("Mapping Master Accounts...")
    
    # Payable Map
    pay_recs = models.execute_kw(DB, uid, PASS, 'account.account', 'search_read', [[('account_type', '=', 'liability_payable')]], {'fields': ['id', 'name', 'code', 'company_ids']})
    comp_pay_map = {}
    for r in pay_recs:
        # Prioritize accounts with code '201002' or name 'Payable(s)'
        if r['code'] == '201002' or r['name'].lower() in ['payable', 'payables']:
            for cid in r['company_ids']:
                if cid not in comp_pay_map:
                    comp_pay_map[cid] = r['id']
    
    # Suspense Map
    suspense_recs = models.execute_kw(DB, uid, PASS, 'account.account', 'search_read', [[('name', 'ilike', 'suspense')]], {'fields': ['id', 'company_ids']})
    comp_susp_map = {}
    for r in suspense_recs:
        for cid in r['company_ids']:
            if cid not in comp_susp_map:
                 comp_susp_map[cid] = r['id']

    print(f"Payable Map: {comp_pay_map}")
    print(f"Suspense Map: {comp_susp_map}")

    # 2. Fetch ALL unreconciled payable lines across ALL companies
    print("Fetching all unreconciled payable lines...")
    domain = [('account_type', '=', 'liability_payable'), ('reconciled', '=', False)]
    lines = models.execute_kw(DB, uid, PASS, 'account.move.line', 'search_read', [domain], {'fields': ['id', 'partner_id', 'company_id', 'debit', 'credit', 'amount_residual', 'account_id']})
    print(f"Found {len(lines)} lines.")

    # 3. Group by (Partner, Company)
    partner_comp_groups = {}
    for l in lines:
        if not l['partner_id']: continue
        key = (l['partner_id'][0], l['company_id'][0])
        if key not in partner_comp_groups: partner_comp_groups[key] = []
        partner_comp_groups[key].append(l)

    # 4. Stage 1: Local Unification and Reconciliation
    print("\nSTAGE 1: Local Unification and Reconciliation...")
    total_unified = 0
    total_local_reconciled = 0
    ctx = {'check_move_validity': False, 'check_company': False}

    for key, l_list in partner_comp_groups.items():
        pid, cid = key
        target_pay_acc = comp_pay_map.get(cid)
        if not target_pay_acc: continue
        
        # Unify to local master account if needed
        to_unify = [l['id'] for l in l_list if l['account_id'][0] != target_pay_acc]
        if to_unify:
            try:
                models.execute_kw(DB, uid, PASS, 'account.move.line', 'write', [to_unify, {'account_id': target_pay_acc}], {'context': ctx})
                total_unified += len(to_unify)
                # Refresh local account data
                for l in l_list:
                    if l['id'] in to_unify: l['account_id'] = [target_pay_acc]
            except Exception as e:
                print(f"  Unify Failed (P:{pid}, C:{cid}): {e}")

        # Local FIFO Reconciliation
        debits = sorted([l for l in l_list if l['debit'] > 0], key=lambda x: x['id'])
        credits = sorted([l for l in l_list if l['credit'] > 0], key=lambda x: x['id'])
        
        for c in credits:
            c_res = abs(c['amount_residual'])
            if c_res <= 0.01: continue
            for d in debits:
                d_res = abs(d['amount_residual'])
                if d_res <= 0.01: continue
                
                try:
                    models.execute_kw(DB, uid, PASS, 'account.move.line', 'reconcile', [[c['id'], d['id']]])
                    total_local_reconciled += 1
                    consumed = min(c_res, d_res)
                    # Update local residual (keep signs!)
                    c_res -= consumed
                    d_res -= consumed
                    c['amount_residual'] = -c_res
                    d['amount_residual'] = d_res
                    
                    if c_res <= 0.01: break
                except Exception as e:
                    if "cannot marshal None" in str(e):
                        total_local_reconciled += 1
                        consumed = min(c_res, d_res)
                        c_res -= consumed
                        d_res -= consumed
                        c['amount_residual'] = -c_res
                        d['amount_residual'] = d_res
                        if c_res <= 0.01: break
                    else:
                        break

    # 5. Stage 2: Global Netting for Cross-Company Mismatches
    print("\nSTAGE 2: Global Netting Settlement...")
    total_settled_moves = 0
    
    # Regroup by Partner to see global net per company
    partner_global = {}
    for key, l_list in partner_comp_groups.items():
        pid, cid = key
        # Sum current residuals (after stage 1)
        branch_net = sum(l['amount_residual'] for l in l_list)
        if abs(branch_net) > 0.01:
            if pid not in partner_global: partner_global[pid] = {'branches': {}, 'name': l_list[0]['partner_id'][1]}
            partner_global[pid]['branches'][cid] = branch_net

    for pid, data in partner_global.items():
        branches = data['branches']
        if len(branches) < 2: 
            continue
        
        # Check if there's both debit and credit across branches
        has_pos = any(v > 0.01 for v in branches.values())
        has_neg = any(v < -0.01 for v in branches.values())
        if not (has_pos and has_neg): 
            continue
        
        print(f"Partner {pid} ({data['name']}): Global Settlement Required. Branches: {branches}")
        
        for cid, branch_net in branches.items():
            suspense_acc = comp_susp_map.get(cid)
            pay_acc = comp_pay_map.get(cid)
            if not suspense_acc or not pay_acc: continue
            
            # Find journal
            journal = models.execute_kw(DB, uid, PASS, 'account.journal', 'search', [[('type', '=', 'general'), ('company_id', '=', cid)]], {'limit': 1})
            if not journal:
                 journal = models.execute_kw(DB, uid, PASS, 'account.journal', 'search', [[('company_id', '=', cid)]], {'limit': 1})
            if not journal: continue

            print(f"  Settling Branch {cid} net {branch_net}...")
            move_vals = {
                'move_type': 'entry',
                'company_id': cid,
                'journal_id': journal[0],
                'date': '2025-01-18',
                'ref': f"Migration Settlement - Global Netting ({data['name']})",
                'line_ids': [
                    (0, 0, {
                        'name': 'Global Netting Settlement',
                        'partner_id': pid,
                        'account_id': pay_acc,
                        'debit': abs(branch_net) if branch_net < 0 else 0,
                        'credit': branch_net if branch_net > 0 else 0,
                    }),
                    (0, 0, {
                        'name': 'Global Netting Offset',
                        'account_id': suspense_acc,
                        'debit': branch_net if branch_net > 0 else 0,
                        'credit': abs(branch_net) if branch_net < 0 else 0,
                    }),
                ]
            }
            try:
                move_id = models.execute_kw(DB, uid, PASS, 'account.move', 'create', [move_vals])
                models.execute_kw(DB, uid, PASS, 'account.move', 'action_post', [[move_id]])
                total_settled_moves += 1
                
                # Reconcile again in this branch
                all_unrec = models.execute_kw(DB, uid, PASS, 'account.move.line', 'search', [[
                    ('partner_id', '=', pid),
                    ('company_id', '=', cid),
                    ('account_id', '=', pay_acc),
                    ('reconciled', '=', False)
                ]])
                if len(all_unrec) > 1:
                    try:
                        models.execute_kw(DB, uid, PASS, 'account.move.line', 'reconcile', [all_unrec])
                    except Exception: pass
            except Exception as e:
                print(f"    Settlement Failed for Comp {cid}: {e}")

    print(f"\nFinal Summary:")
    print(f"Total Lines Unified Locally: {total_unified}")
    print(f"Total Local Reconciliations: {total_local_reconciled}")
    print(f"Total Global Settlement Moves: {total_settled_moves}")

if __name__ == "__main__":
    main()
