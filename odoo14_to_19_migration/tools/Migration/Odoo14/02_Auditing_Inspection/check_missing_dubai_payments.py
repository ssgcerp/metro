import xmlrpc.client
import ssl
import pandas as pd
import os

url = 'https://metro.equdaierp.com'
src_db = 'metrodb'
dest_db = 'newdb'
username = 'admin'
password = 'Amaze@321'
company_name = 'DUBAI'
excel_map = 'journal_mapping_template.xlsx'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context(), allow_none=True)
src_uid = common.authenticate(src_db, username, password, {})
dest_uid = common.authenticate(dest_db, username, password, {})

src_models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context(), allow_none=True)
dest_models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context(), allow_none=True)

# Load Excel map
df = pd.read_excel(excel_map)
journal_map = {}
for index, row in df.iterrows():
    if str(row['Source Company']) == company_name:
        src_j_id = int(row['Source Journal ID'])
        journal_map[src_j_id] = row['Source Journal Name']

src_company_id = src_models.execute_kw(src_db, src_uid, password, 'res.company', 'search', [[('name', '=', company_name)]])[0]

domain = [
    ('payment_type', '=', 'inbound'),
    ('partner_type', '=', 'customer'),
    ('state', 'in', ['paid', 'in_process', 'posted']),
    ('company_id', '=', src_company_id)
]

src_pays = src_models.execute_kw(src_db, src_uid, password, 'account.payment', 'search_read', [domain], {'fields': ['name', 'journal_id', 'state']})
print(f"Total source inbound customer payments for {company_name}: {len(src_pays)}")

missing = []
unmapped_journals = set()

for pay in src_pays:
    pay_name = pay['name']
    src_j_id = pay['journal_id'][0]
    src_j_name = pay['journal_id'][1]
    
    # Check if this payment exists in the dest db
    dest_count = dest_models.execute_kw(dest_db, dest_uid, password, 'account.payment', 'search_count', [[('name', '=', pay_name)]])
    
    if dest_count == 0:
        reason = ""
        if src_j_id not in journal_map:
            reason = f"Journal '{src_j_name}' (ID {src_j_id}) not mapped in Excel"
            unmapped_journals.add(f"{src_j_name} (ID {src_j_id})")
        else:
            reason = "Unknown/Failed during creation"
            
        missing.append({'name': pay_name, 'journal': src_j_name, 'reason': reason, 'state': pay['state']})

print(f"\nFound {len(missing)} missing payments out of {len(src_pays)}.")

print("\n--- Missing Payments Summary ---")
for m in missing[:15]:
    print(f"{m['name']} - {m['state']} - {m['reason']}")
if len(missing) > 15:
    print(f"... and {len(missing) - 15} more.")

print("\n--- Unmapped Journals that caused skipping ---")
for j in unmapped_journals:
    print(j)
