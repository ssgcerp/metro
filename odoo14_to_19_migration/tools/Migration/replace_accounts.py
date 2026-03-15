import os

files = [
    r'e:\odoo modules\19\metro\odoo14_to_19_migration\tools\fix_invoice_accounts.py',
    r'e:\odoo modules\19\metro\odoo14_to_19_migration\tools\fix_bill_accounts.py',
    r'e:\odoo modules\19\metro\odoo14_to_19_migration\models\vendor_bill_migration_line.py',
    r'e:\odoo modules\19\metro\odoo14_to_19_migration\docs\VENDOR_BILL_MAPPING_VERIFICATION_REPORT.md',
    r'C:\Users\karth\.gemini\antigravity\brain\170a6528-fe4b-48a7-b636-415b87387361\vendor_bill_migration_analysis.md'
]

for f_path in files:
    if os.path.exists(f_path):
        with open(f_path, 'r', encoding='utf-8') as f:
            content = f.read()
        new_content = content.replace('501100', '400001').replace('PURCHASE EXPENSES', 'Cost of Goods Sold in Trading')
        # Also replace lower case variants just in case
        new_content = new_content.replace('purchase expenses', 'cost of goods sold in trading')
        if new_content != content:
            with open(f_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'Updated {f_path}')
        else:
            print(f'No changes for {f_path}')
    else:
        print(f'File not found: {f_path}')
