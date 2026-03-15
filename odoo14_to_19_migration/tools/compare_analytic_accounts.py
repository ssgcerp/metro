import xmlrpc.client

# Odoo 18 (Source)
url_18 = "https://metro-fire-system-llc.odoo.com"
db_18 = "metro-fire-system-llc"
username_18 = "sruthi@metrofiresystems.com"
password_18 = "Sruthi@321"

# Odoo 19 (Destination)
url_19 = "https://metro.equdaierp.com"
db_19 = "metrodb"
username_19 = "admin"
password_19 = "Amaze@321"

def connect(url, db, username, password):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    return uid, models

def compare_analytics():
    print(f"--- Connecting to Odoo 18 ---")
    uid_18, models_18 = connect(url_18, db_18, username_18, password_18)
    print(f"Connected to Odoo 18 (UID: {uid_18})")
    
    print(f"--- Connecting to Odoo 19 ---")
    uid_19, models_19 = connect(url_19, db_19, username_19, password_19)
    print(f"Connected to Odoo 19 (UID: {uid_19})")

    # Fetch Odoo 18 Analytic Accounts
    # We want 'name' and 'code' (Reference)
    # Note: field name for Reference in Odoo 18 is likely 'code' or 'reference', let's check 'code' first as standard
    # If not found, we might need to check fields. Standard Odoo analytic account has 'code' (Reference)
    fields_18 = ['id', 'name', 'code']
    print("Fetching Odoo 18 Analytic Accounts...")
    aa_18 = models_18.execute_kw(db_18, uid_18, password_18, 'account.analytic.account', 'search_read', 
        [[]], {'fields': fields_18})
    print(f"  Found {len(aa_18)} accounts in Odoo 18.")
    
    # Check fields in Odoo 19 to confirm 'code' exists (it usually does)
    # Fetch Odoo 19 Analytic Accounts
    fields_19 = ['id', 'name', 'code']
    print("Fetching Odoo 19 Analytic Accounts...")
    aa_19 = models_19.execute_kw(db_19, uid_19, password_19, 'account.analytic.account', 'search_read',
        [[]], {'fields': fields_19})
    print(f"  Found {len(aa_19)} accounts in Odoo 19.")
    
    # Map 19 by Name AND Code
    map_19_name = {a['name'].strip().lower(): a for a in aa_19}
    map_19_code = {a['code'].strip().upper(): a for a in aa_19 if a.get('code')}
    
    actions = {
        'update_code': [],
        'update_name': [],
        'create': []
    }
    
    print("\n--- Advanced Comparison ---")
    for a18 in aa_18:
        name_18 = a18['name'].strip()
        name_key = name_18.lower()
        code_18 = (a18['code'] or '').strip()
        code_key = code_18.upper()
        
        # Scenario 1: Match by Code (Strong Link)
        if code_18 and code_key in map_19_code:
            a19 = map_19_code[code_key]
            # Check Name
            if a19['name'].strip().lower() != name_key:
                actions['update_name'].append({
                    'id_19': a19['id'],
                    'old_name': a19['name'],
                    'new_name': name_18,
                    'code': code_18
                })
        # Scenario 2: Match by Name (Weak Link)
        elif name_key in map_19_name:
            a19 = map_19_name[name_key]
            # Check Code
            code_19 = (a19['code'] or '').strip()
            if code_18 != code_19:
                actions['update_code'].append({
                    'id_19': a19['id'],
                    'name': name_18,
                    'old_code': code_19,
                    'new_code': code_18
                })
        # Scenario 3: No Match
        else:
             actions['create'].append({
                 'name': name_18,
                 'code': code_18,
                 'partner_id': a18.get('partner_id', False) # We might need this later, but for now just name/code
             })

    import json
    with open('migration_plan.json', 'w', encoding='utf-8') as f:
        json.dump(actions, f, indent=4)
        
    print(f"Plan Generated:")
    print(f"  Update Code (Name matched): {len(actions['update_code'])}")
    print(f"  Update Name (Code matched): {len(actions['update_name'])}")
    print(f"  Create New (Missing):       {len(actions['create'])}")
    
    # Also write readable summary
    with open('analytic_diff_v2.txt', 'w', encoding='utf-8') as f:
        f.write("--- UPDATE CODE (Name Match) ---\n")
        for x in actions['update_code']:
            f.write(f"ID {x['id_19']} | {x['name']} | {x['old_code']} -> {x['new_code']}\n")
            
        f.write("\n--- UPDATE NAME (Code Match) ---\n")
        for x in actions['update_name']:
             f.write(f"ID {x['id_19']} | {x['code']} | {x['old_name']} -> {x['new_name']}\n")
             
        f.write("\n--- CREATE NEW ---\n")
        for x in actions['create']:
            f.write(f"New | {x['name']} | {x['code']}\n")

if __name__ == "__main__":
    compare_analytics()
