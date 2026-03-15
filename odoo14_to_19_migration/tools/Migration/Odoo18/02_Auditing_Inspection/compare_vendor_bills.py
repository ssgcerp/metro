import xmlrpc.client
import ssl
import pandas as pd
from datetime import datetime

# Odoo 19 Credentials (Target)
url_19 = 'https://metro.equdaierp.com'
db_19 = 'newdb'
user_19 = 'admin'
pass_19 = 'Amaze@321'

# Odoo 18 Credentials (Source)
url_18 = 'https://metro-fire-system-llc.odoo.com'
db_18 = 'metro-fire-system-llc'
user_18 = 'sruthi@metrofiresystems.com'
pass_18 = 'Sruthi@321'

ctx = ssl._create_unverified_context()

def get_models(url, db, user, password):
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ctx, allow_none=True)
    uid = common.authenticate(db, user, password, {})
    if not uid:
        raise Exception(f"Failed to authenticate to {url}")
    return uid, xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ctx, allow_none=True)

print("Connecting to Odoo instances...")
uid_19, models_19 = get_models(url_19, db_19, user_19, pass_19)
uid_18, models_18 = get_models(url_18, db_18, user_18, pass_18)

# Load Excel
df_excel = pd.read_excel(r'e:\odoo modules\19\metro\odoo14_to_19_migration\tools\Reset\correct_vendor_bills.xlsx')
excel_numbers = [str(n).strip() for n in df_excel['Number'].dropna().tolist()]

# Map number -> excel total
excel_totals = {}
if 'Total' in df_excel.columns:
    for _, row in df_excel.iterrows():
        num = str(row['Number']).strip()
        excel_totals[num] = abs(row['Total']) if pd.notna(row['Total']) else None

print(f"Total bills in Excel: {len(excel_numbers)}")

# Fetch data from Odoo 19
print("Fetching vendor bills from Odoo 19...")
o19_data = {}  # name -> {'total': X, 'partner': Y}
domain_19 = [('move_type', 'in', ['in_invoice', 'in_receipt'])]
batch_size = 500
offset = 0
while True:
    results = models_19.execute_kw(db_19, uid_19, pass_19, 'account.move', 'search_read', [domain_19],
                                   {'fields': ['name', 'amount_total', 'partner_id'], 'limit': batch_size, 'offset': offset})
    if not results:
        break
    for r in results:
        name = str(r['name']).strip()
        partner = r['partner_id'][1] if r['partner_id'] else ''
        o19_data[name] = {'total': r['amount_total'], 'partner': partner}
    offset += batch_size
    print(f"  Fetched {offset} from Odoo 19...")

# Fetch data from Odoo 18
# Instead of fetching everything, we can search for the specific names in Excel
print("Fetching vendor bills from Odoo 18...")
o18_data = {}  # name -> partner
batch_size = 200
for i in range(0, len(excel_numbers), batch_size):
    batch_nums = excel_numbers[i:i + batch_size]
    domain_18 = [('move_type', 'in', ['in_invoice', 'in_receipt']), ('name', 'in', batch_nums)]
    results = models_18.execute_kw(db_18, uid_18, pass_18, 'account.move', 'search_read', [domain_18],
                                   {'fields': ['name', 'partner_id']})
    for r in results:
        name = str(r['name']).strip()
        partner = r['partner_id'][1] if r['partner_id'] else ''
        o18_data[name] = partner
    print(f"  Processed {i + len(batch_nums)} numbers from Excel list against Odoo 18...")

# Build report
report_rows = []
for n in excel_numbers:
    excel_total = excel_totals.get(n)
    
    # O19 Data
    d19 = o19_data.get(n)
    o19_total = d19['total'] if d19 else None
    o19_partner = d19['partner'] if d19 else ''
    
    # O18 Data
    o18_partner = o18_data.get(n, '')

    if o19_total is not None:
        status = 'Found in Odoo 19'
        diff = round(o19_total - excel_total, 2) if excel_total is not None else 'N/A'
    else:
        status = 'MISSING in Odoo 19'
        diff = 'N/A'
        
    report_rows.append({
        'Bill Number (Excel)': n,
        'Odoo 18 Customer': o18_partner,
        'Odoo 19 Customer': o19_partner,
        'Excel Total': excel_total,
        'Odoo 19 Total': o19_total if o19_total is not None else '',
        'Difference': diff,
        'Status': status
    })

df_report = pd.DataFrame(report_rows)
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
report_file = f"missing_vendor_bills_report_{timestamp}.xlsx"

with pd.ExcelWriter(report_file, engine='openpyxl') as writer:
    df_report.to_excel(writer, sheet_name='All Bills', index=False)
    df_missing = df_report[df_report['Status'] == 'MISSING in Odoo 19']
    df_missing.to_excel(writer, sheet_name='Missing Only', index=False)
    df_mismatch = df_report[
        (df_report['Status'] == 'Found in Odoo 19') &
        (df_report['Difference'] != 0) &
        (df_report['Difference'] != 'N/A')
    ]
    df_mismatch.to_excel(writer, sheet_name='Amount Mismatch', index=False)

print(f"\nReport saved: {report_file}")
print(f"Total processed: {len(excel_numbers)}")
print(f"Missing from Odoo 19: {len(df_missing)}")
