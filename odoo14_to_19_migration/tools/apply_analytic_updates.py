import xmlrpc.client
import json

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def apply_updates():
    print(f"--- Applying Analytic Account Updates to Odoo 19 ---")
    
    try:
        with open('migration_plan.json', 'r', encoding='utf-8') as f:
            plan = json.load(f)
    except FileNotFoundError:
        print("migration_plan.json not found!")
        return

    # 1. Update Codes
    to_update_code = plan.get('update_code', [])
    print(f"Updating Codes for {len(to_update_code)} accounts...")
    for item in to_update_code:
        try:
            models.execute_kw(db, uid, password, 'account.analytic.account', 'write',
                [[item['id_19']], {'code': item['new_code']}])
            print(f"  Updated ID {item['id_19']}: Code {item['old_code']} -> {item['new_code']}")
        except Exception as e:
            print(f"  Error updating ID {item['id_19']}: {e}")

    # 2. Update Names
    to_update_name = plan.get('update_name', [])
    print(f"\nUpdating Names for {len(to_update_name)} accounts...")
    for item in to_update_name:
        try:
            models.execute_kw(db, uid, password, 'account.analytic.account', 'write',
                [[item['id_19']], {'name': item['new_name']}])
            print(f"  Updated ID {item['id_19']}: Name {item['old_name']} -> {item['new_name']}")
        except Exception as e:
            print(f"  Error updating ID {item['id_19']}: {e}")

    # 3. Create New
    to_create = plan.get('create', [])
    print(f"\nCreating {len(to_create)} new accounts...")
    
    # We use Plan ID = 1 (Project) as discovered
    PLAN_ID = 1
    
    batch_size = 50
    for i in range(0, len(to_create), batch_size):
        batch = to_create[i:i+batch_size]
        vals_list = []
        for item in batch:
            vals = {
                'name': item['name'],
                'code': item['code'],
                'plan_id': PLAN_ID,
                # 'partner_id': ... skipping for now
            }
            vals_list.append(vals)
            
        if vals_list:
            try:
                new_ids = models.execute_kw(db, uid, password, 'account.analytic.account', 'create', [vals_list])
                print(f"  Created Batch {i}-{i+len(batch)}: {len(new_ids)} records.")
            except Exception as e:
                print(f"  Error creating batch {i}: {e}")
                # Fallback: Try one by one
                print("  Trying one by one...")
                for v in vals_list:
                    try:
                        nid = models.execute_kw(db, uid, password, 'account.analytic.account', 'create', [v])
                        print(f"    Created {v['name']} -> ID {nid}")
                    except Exception as ex:
                        print(f"    Failed {v['name']}: {ex}")

    print("\n--- Done ---")

if __name__ == "__main__":
    apply_updates()
