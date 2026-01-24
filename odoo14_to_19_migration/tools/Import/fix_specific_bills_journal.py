
import pandas as pd
import shutil
import os

file_path = r"e:\odoo modules\19\metro\odoo14_to_19_migration\Export\VendorPayments_Export.xlsx"
backup_path = r"e:\odoo modules\19\metro\odoo14_to_19_migration\Export\VendorPayments_Export_SPECIFIC_BACKUP.xlsx"

target_bills = [
    "BILL/2025/04/0021",
    "BILL/2025/04/0022",
    "BILL/2025/06/0089",
    "BILL/2025/07/0076",
    "BILL/2025/09/0028",
    "BILL/2025/09/0029",
    "EXP/2025/01/0482",
    "EXP/2025/04/0037",
    "EXP/2025/08/0043",
    "EXP/2025/08/0057"
]

target_journal = "Petty Cash - DUBAI"

print("-" * 80)
print("FIXING SPECIFIC BILL JOURNALS")
print("-" * 80)

# 1. Backup
if os.path.exists(file_path):
    shutil.copy2(file_path, backup_path)
    print(f"Backed up original file to: {backup_path}")
else:
    print(f"File not found: {file_path}")
    exit(1)

# 2. Read Excel
df = pd.read_excel(file_path)
print(f"Loaded {len(df)} rows.")

updated_count = 0

# 3. Apply Logic
for index, row in df.iterrows():
    bill_nums_raw = str(row.get('Linked Bill Numbers', ''))
    # Clean and split
    bills = [b.strip() for b in bill_nums_raw.split(',') if b.strip() and b.lower() != 'nan']
    
    # Check if ANY of the bills in this row match our target list
    match_found = False
    for b in bills:
        if b in target_bills:
            match_found = True
            break
            
    if match_found:
        current_journal = row.get('Journal')
        if current_journal != target_journal:
            print(f"Row {index+2}: Found Bill match. Changing Journal '{current_journal}' -> '{target_journal}'")
            df.at[index, 'Journal'] = target_journal
            updated_count += 1
        else:
            print(f"Row {index+2}: Found Bill match, but Journal is already correct ({current_journal}).")

# 4. Save
if updated_count > 0:
    df.to_excel(file_path, index=False)
    print(f"\nSaved updated file to: {file_path}")
    print(f"Total rows updated: {updated_count}")
else:
    print("\nNo rows matched the criteria (or they were already correct). File unchanged.")
