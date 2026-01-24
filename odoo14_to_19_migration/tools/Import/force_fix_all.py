
import xmlrpc.client
import sys
import time

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print("="*80)
    print("FORCE FIX ALL IN PROCESS PAYMENTS")
    print("="*80)
    
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    # 1. Search ALL In Process
    domain = [('state', '=', 'in_process'), ('partner_type', '=', 'supplier')]
    ids = models.execute_kw(DB, uid, PASS, 'account.payment', 'search', [domain])
    print(f"Found {len(ids)} payments to fix.")
    
    if not ids:
        print("Done.")
        return

    # 2. Read Journals
    print("Grouping by Journal...")
    chunk_size = 2000
    pay_data = []
    for i in range(0, len(ids), chunk_size):
        chunk = ids[i:i+chunk_size]
        res = models.execute_kw(DB, uid, PASS, 'account.payment', 'read', [chunk, ['journal_id']])
        pay_data.extend(res)
        
    j_map = {} # jid -> [pids]
    for p in pay_data:
        if not p.get('journal_id'): continue
        jid = p['journal_id'][0]
        if jid not in j_map:
            j_map[jid] = {'name': p['journal_id'][1], 'ids': []}
        j_map[jid]['ids'].append(p['id'])
        
    print(f"Grouped into {len(j_map)} Journals.")
    
    # 3. Process Per Journal
    for jid, data in j_map.items():
        print(f"Processing Journal '{data['name']}' ({len(data['ids'])} payments)...")
        
        # Get Bank Account
        j_info = models.execute_kw(DB, uid, PASS, 'account.journal', 'read', [[jid], ['default_account_id']])[0]
        bank_id = j_info.get('default_account_id')
        if bank_id: 
            bank_id = bank_id[0]
        else:
            print(f"  -> WARNING: Journal has NO Default Account! Skipping {len(data['ids'])} payments.")
            continue
            
        print(f"  -> Target Account: {bank_id}. Writing...")
        
        # Batch Write
        batch_size = 500
        pids = data['ids']
        for i in range(0, len(pids), batch_size):
            batch = pids[i:i+batch_size]
            try:
                models.execute_kw(DB, uid, PASS, 'account.payment', 'write', [batch, {'outstanding_account_id': bank_id}])
                print(f"     Updated {len(batch)} records.")
            except Exception as e:
                print(f"     FAILED batch: {e}")
                
    print("\nVerification Count:")
    rem_ids = models.execute_kw(DB, uid, PASS, 'account.payment', 'search', [domain])
    print(f"Remaining In Process: {len(rem_ids)}")

if __name__ == "__main__":
    main()
