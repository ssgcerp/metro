import pandas as pd
import xmlrpc.client

# Odoo 19 Credentials (Source - metrodb)
URL_SRC = 'https://metro.equdaierp.com'
DB_SRC = 'metrodb'
USER_SRC = 'admin'
PASS_SRC = 'Amaze@321'

common_src = xmlrpc.client.ServerProxy(f'{URL_SRC}/xmlrpc/2/common', allow_none=True)
uid_src = common_src.authenticate(DB_SRC, USER_SRC, PASS_SRC, {})
models_src = xmlrpc.client.ServerProxy(f'{URL_SRC}/xmlrpc/2/object', allow_none=True)

domain_src = [('payment_type', '=', 'inbound'), ('partner_type', '=', 'customer'), ('state', 'in', ['in_process', 'paid', 'posted'])]
payments = models_src.execute_kw(DB_SRC, uid_src, PASS_SRC, 'account.payment', 'search_read', 
    [domain_src], {'fields': ['journal_id', 'company_id']})

print(f'Total inbound customer payments found: {len(payments)}')

used_journals = set()
for p in payments:
    j = p.get('journal_id')
    c = p.get('company_id')
    if isinstance(j, list) and len(j) > 1:
        j_name = j[1] 
    else: 
        j_name = 'None'
    if isinstance(c, list) and len(c) > 1:
        c_name = c[1] 
    else: 
        c_name = 'None'
    used_journals.add((j_name, c_name))

df = pd.read_excel(r'e:\odoo modules\19\metro\odoo14_to_19_migration\tools\journal_mapping_metrodb_to_newdb.xlsx')

mapping = set()
for _, row in df.iterrows():
    src_name = row['Source Name (metrodb)']
    src_comp = row['Source Company']
    tgt_name = row['Target Name (newdb)']
    if pd.notna(tgt_name) and str(tgt_name).strip() != '':
        mapping.add((src_name, src_comp))

missing_mysore = []
for j_name, c_name in used_journals:
    if (j_name, c_name) not in mapping and "Mysore" in str(c_name):
        missing_mysore.append((j_name, c_name))

if missing_mysore:
    print('Still missing mappings in Excel for the following used journals in Mysore Restaurant:')
    for j, c in missing_mysore:
        print(f'  - Journal: "{j}" | Company: "{c}"')
else:
    print('All journals used in payments for Mysore Restaurant have a mapping in the Excel file!')
