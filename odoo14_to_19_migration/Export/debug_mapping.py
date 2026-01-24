import pandas as pd
import sys

def debug_import_logic():
    file_path = r"e:\odoo modules\19\metro\odoo14_to_19_migration\Export\VendorBills_RAS_AL_KHAIMAH.xlsx"
    
    print(f"Reading file: {file_path}")
    try:
        df = pd.read_excel(file_path)
    except FileNotFoundError:
        print("File not found.")
        return

    # Clean Columns
    df.columns = df.columns.str.strip()
    
    # Required Header Columns
    header_cols = [
        'Number', 'Company', 'Partner', 'Journal*', 'Invoice Bill Date', 
        'Accounting Date', 'Due Date', 'Bill Reference'
    ]
    
    # Verify exist
    existing_headers = [c for c in header_cols if c in df.columns]
    
    # Apply forward fill for header columns
    df[existing_headers] = df[existing_headers].ffill()
    
    # Drop rows where 'Number' AND 'Bill Reference' are NaN (assuming we need at least one)
    # The original script dropped subset=['Number', 'Bill Reference']
    df.dropna(subset=['Number', 'Bill Reference'], inplace=True)
    
    # print(f"Columns: {df.columns.tolist()}") # Removed noisy print
    
    # Group by Bill Reference (as in the script)
    grouped = df.groupby('Bill Reference', sort=False)
    
    # print(f"Total Groups: {len(grouped)}") # Removed noisy print
    
    found_target = False
    
    for bill_ref, group in grouped:
        row = group.iloc[0]
        
        number = row['Number']
        ref = row['Bill Reference']
        
        # Check if this group matches our failing case
        # Failing case: Number should be EXP/2025/08/0207
        # Note: In the excel, we found EXP/2025/08/0207 in the 'Number' column, and '8460...' in Ref.
        
        match = False
        if str(number).strip() == 'EXP/2025/08/0207':
            match = True
        if str(ref).strip() == 'EXP/2025/08/0207':
            match = True
            
        if match:
            found_target = True
            with open("debug_output.txt", "w") as f:
                f.write("\n--- MATCH FOUND ---\n")
                f.write(f"Group Key (Bill Ref): {bill_ref}\n")
                f.write(f"Row Number: {number}\n")
                f.write(f"Row Ref: {ref}\n")
                f.write(f"Mapped Name (to be sent to Odoo): {number}\n")
                f.write(f"Mapped Ref (to be sent to Odoo): {ref}\n")
                f.write("-" * 20 + "\n")
            print("Finished writing to debug_output.txt")

    if not found_target:
        print("\nTarget EXP/2025/08/0207 not found in any processed group.")

if __name__ == "__main__":
    debug_import_logic()
