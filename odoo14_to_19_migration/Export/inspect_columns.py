import pandas as pd
import os

file_path = r"e:\odoo modules\19\metro\odoo14_to_19_migration\Export\VendorBills_RAS_AL_KHAIMAH.xlsx"

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
else:
    df = pd.read_excel(file_path)
    # Prints removed

    
    # Search for the specific reference seen in screenshot
    target_ref = "EXP/2025/09/0354"
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
pd.set_option('display.max_colwidth', None)

if 152 in df.index:
    num = df.loc[152, 'Number']
    ref = df.loc[152, 'Bill Reference']
    print(f"ROW 152 NUMBER: {num}")
    print(f"ROW 152 REFERENCE: {ref}")
else:
    print("Row 152 not found")

with open("debug_output_inspection.txt", "w") as f:
    target_term = "EXP/2025/08/0199"
    f.write(f"Searching for {target_term}\n")
    
    target_rows = df[df['Bill Reference'].astype(str).str.contains(target_term, na=False)]
    if not target_rows.empty:
        f.write(f"\n--- Found '{target_term}' in Bill Reference ---\n")
        max_rows = 10
        count = 0
        for idx, row in target_rows.iterrows():
            f.write(f"Index: {idx}\nNumber: '{row['Number']}'\nReference: '{row['Bill Reference']}'\n\n")
            count += 1
            if count >= max_rows: break
    
    target_rows_num = df[df['Number'].astype(str).str.contains(target_term, na=False)]
    if not target_rows_num.empty:
        f.write(f"\n--- Found '{target_term}' in Number ---\n")
        max_rows = 10
        count = 0
        for idx, row in target_rows_num.iterrows():
            f.write(f"Index: {idx}\nNumber: '{row['Number']}'\nReference: '{row['Bill Reference']}'\n\n")
            count += 1
            if count >= max_rows: break
    
    print("Output written to debug_output_inspection.txt")
