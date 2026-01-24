
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print("SYNCHRONIZING PAYMENT MOVE LINES")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
    
    # 1. Search Supplier Payments that are Posted/Paid
    # We want to fix the ones causing 'In Payment' bills.
    # So let's look for ALL supplier payments.
    print("Searching payments...")
    domain = [('partner_type', '=', 'supplier'), ('state', 'in', ['posted', 'paid'])]
    ids = models.execute_kw(DB, uid, PASS, 'account.payment', 'search', [domain])
    print(f"Found {len(ids)} payments.")
    
    batch_size = 500
    ctx = {'check_move_validity': False, 'check_company': False} # Safe context
    
    total_fixed = 0
    
    print("Starting efficient batch processing...")

    # Reworked Loop
    print("Restarting with efficient loop...")
    p_data = models.execute_kw(DB, uid, PASS, 'account.payment', 'read', [ids, ['move_id', 'outstanding_account_id', 'destination_account_id']])
    
    updates = [] # List of (line_id, new_acc_id)
    
    for p in p_data:
        if not p['move_id']: continue
        if not p['outstanding_account_id']: continue
        
        target_acc = p['outstanding_account_id'][0]
        dest_acc = p['destination_account_id'][0] if p['destination_account_id'] else False
        move_id = p['move_id'][0]
        
        # We need lines.Fetching 3000 moves lines is heavy.
        # But we must.
        # Let's do it in chunks of payments to avoid memory issues.
        pass

    # Actually, execute the loop properly
    chunk_p_data = [p_data[i:i+100] for i in range(0, len(p_data), 100)]
    
    for chunk in chunk_p_data:
        mids = [x['move_id'][0] for x in chunk if x['move_id']]
        if not mids: continue
        
        # Get all lines for these moves
        all_lines = models.execute_kw(DB, uid, PASS, 'account.move.line', 'search_read', [[('move_id', 'in', mids)]], {'fields': ['move_id', 'account_id', 'id']})
        
        # Map move_id -> lines
        map_lines = {}
        for l in all_lines:
            mid = l['move_id'][0]
            if mid not in map_lines: map_lines[mid] = []
            map_lines[mid].append(l)
            
        # Analyze mismatch
        for p in chunk:
            if not p.get('move_id'):
                continue
            mid = p['move_id'][0]
            target_acc = p['outstanding_account_id'][0] if p.get('outstanding_account_id') else False
            dest_acc = p['destination_account_id'][0] if p.get('destination_account_id') else -1
            
            if not target_acc: continue
            
            if mid not in map_lines: continue
            
            lines = map_lines[mid]
            # Find the line that needs update.
            # It is the line that is NOT dest_acc.
            # AND is NOT already target_acc.
            
            for l in lines:
                lid = l['id']
                l_acc = l['account_id'][0]
                
                if l_acc != dest_acc:
                    # This is the candidate.
                    if l_acc != target_acc:
                        # Mismatch! Update this line.
                        print(f"Fixing Payment {p['id']} (Move {mid}): Line {lid} Acc {l_acc} -> {target_acc}")
                        try:
                            models.execute_kw(DB, uid, PASS, 'account.move.line', 'write', [[lid], {'account_id': target_acc}], {'context': ctx})
                            total_fixed += 1
                        except Exception as e:
                            print(f"  Fail: {e}")
                            
    print(f"Total Lines Fixed: {total_fixed}")

if __name__ == "__main__":
    main()
