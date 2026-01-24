
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

# Mapping from Report
# [Bill List] -> Target Company Name
MOVES = [
    # ABU DHABI -> AJMAN
    {'bills': ['EXP/2025/05/0037'], 'to': 'AJMAN'},
    
    # ABU DHABI -> DUBAI
    {'bills': ['BILL/2025/07/0071', 'EXP/2025/12/0031'], 'to': 'DUBAI'},
    
    # ABU DHABI -> FUJAIRAH
    {'bills': ['EXP/2025/02/0180', 'EXP/2025/05/0209'], 'to': 'FUJAIRAH'},
    
    # SHARJAH -> FUJAIRAH
    {'bills': ['SI-550100035553'], 'to': 'FUJAIRAH'},
    
    # ABU DHABI -> RAS AL KHAIMAH
    {'bills': ['EXP/2025/07/0063'], 'to': 'RAS AL KHAIMAH'},
    
    # ABU DHABI -> SHARJAH
    {'bills': ['BILL/2025/09/0001'], 'to': 'SHARJAH'},
    
    # SHARJAH -> ABU DHABI
    {'bills': ['BILL/2025/11/0053', 'EXP/2025/10/0038'], 'to': 'ABU DHABI'},
]

def main():
    print("Connecting to Odoo...")
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL))
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL))
    
    # Context to bypass company rules
    # Get all company IDs first
    companies = models.execute_kw(DB, uid, PASS, 'res.company', 'search', [[]])
    ctx = {'allowed_company_ids': companies}
    
    # Resolve Target Company IDs
    comp_map = {}
    print("Resolving Company IDs...")
    for item in MOVES:
        t_name = item['to']
        if t_name not in comp_map:
            res = models.execute_kw(DB, uid, PASS, 'res.company', 'search', [[('name', 'ilike', t_name)]], {'limit':1})
            if res:
                comp_map[t_name] = res[0]
                print(f"  Mapped '{t_name}' -> ID {res[0]}")
            else:
                print(f"  ERROR: Could not find company '{t_name}'")

    print("\nStarting Fixes...")
    
    for item in MOVES:
        target_name = item['to']
        target_id = comp_map.get(target_name)
        if not target_id:
            continue
            
        bills = item['bills']
        for bill_ref in bills:
            print(f"Processing {bill_ref} -> {target_name}...")
            
            # Find Bill
            # Search by name OR ref
            domain = ['|', ('name', '=', bill_ref), ('ref', '=', bill_ref)]
            # Bill must be in_invoice
            domain = ['&', ('move_type', '=', 'in_invoice')] + domain
            
            # Use universal context
            bill_ids = models.execute_kw(DB, uid, PASS, 'account.move', 'search', [domain], {'context': ctx, 'limit': 1})
            
            if not bill_ids:
                print(f"  -> Bill {bill_ref} NOT FOUND in Odoo.")
                continue
                
            bill_id = bill_ids[0]
            
            # Read Check
            bill_data = models.execute_kw(DB, uid, PASS, 'account.move', 'read', [bill_id], {'fields': ['company_id', 'state', 'partner_id'], 'context': ctx})[0]
            curr_comp_id = bill_data['company_id'][0]
            
            if curr_comp_id == target_id:
                print(f"  -> Already in correct company ({target_id}). Skipping.")
                continue
                
            # PERFORM MOVE
            # 1. Reset to Draft if Posted (Wait, if cancelled? we check)
            if bill_data['state'] == 'posted':
                 models.execute_kw(DB, uid, PASS, 'account.move', 'button_draft', [[bill_id]], {'context': ctx})
                 print("  -> Reset to Draft.")
            elif bill_data['state'] == 'cancel':
                 models.execute_kw(DB, uid, PASS, 'account.move', 'button_draft', [[bill_id]], {'context': ctx})
                 print("  -> Reset from Cancel to Draft.")

            # 2. Fix Partner (Shared if needed)
            partner_id = bill_data['partner_id'][0]
            p_data = models.execute_kw(DB, uid, PASS, 'res.partner', 'read', [partner_id], {'fields': ['company_id'], 'context': ctx})[0]
            p_comp_id = p_data['company_id'][0] if p_data['company_id'] else False
            
            if p_comp_id and p_comp_id != target_id:
                print(f"  -> Making Partner Shared (was {p_comp_id}).")
                models.execute_kw(DB, uid, PASS, 'res.partner', 'write', [[partner_id], {'company_id': False}], {'context': ctx})
            
            # 3. Update Company (Header + Lines)
            # Update Header
            models.execute_kw(DB, uid, PASS, 'account.move', 'write', [[bill_id], {'company_id': target_id, 'journal_id': False}], {'context': ctx})
            
            # Update Lines
            lines = models.execute_kw(DB, uid, PASS, 'account.move.line', 'search', [[('move_id', '=', bill_id)]], {'context': ctx})
            if lines:
                models.execute_kw(DB, uid, PASS, 'account.move.line', 'write', [lines, {'company_id': target_id}], {'context': ctx})
            
            print(f"  -> Moved to Company {target_id}.")
            
            # 4. Post?
            # User usually wants it posted, but maybe safer to leave draft for review?
            # Let's try to post.
            try:
                models.execute_kw(DB, uid, PASS, 'account.move', 'action_post', [[bill_id]], {'context': ctx})
                print("  -> Posted successfully.")
            except Exception as e:
                print(f"  -> WARNING: Could not post: {e}")

    print("Done.")

if __name__ == "__main__":
    main()
