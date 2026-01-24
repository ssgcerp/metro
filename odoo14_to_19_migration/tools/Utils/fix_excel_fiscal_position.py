import pandas as pd
import os
import sys

# Target File
file_path = r"e:\odoo modules\19\metro\odoo14_to_19_migration\Export\Odoo18_VendorBills_Metro_Fire_System_LLC_20260109_111059.xlsx"

def main():
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        # Try finding in current dir just in case
        return

    print(f"Reading {file_path}...")
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Failed to read Excel: {e}")
        return

    if 'Fiscal Position' not in df.columns:
        print("Error: Column 'Fiscal Position' not found in Excel.")
        print(f"Columns found: {df.columns.tolist()}")
        return

    print("Applying fixes...")
    
    # 1. Clear Fiscal Position if 'Number' is missing (Secondary lines)
    if 'Number' in df.columns:
        original_count = df['Fiscal Position'].notna().sum()
        df.loc[df['Number'].isna(), 'Fiscal Position'] = None
        new_count = df['Fiscal Position'].notna().sum()
        print(f"Cleared Fiscal Position on {original_count - new_count} secondary lines.")

    # 2. Fix Fiscal Position on Header lines (where Number is present)
    
    def fix_header_fp(row):
        # Skip if not a header row
        if pd.isna(row.get('Number')):
            return None
            
        fp = row.get('Fiscal Position')
        s_fp = str(fp).strip() if pd.notna(fp) else ''
        desc = str(row.get('Description', '')).upper()
        bill_ref = str(row.get('Bill Reference', '')).upper()
        
        # Combine text for searching (Description + Bill Reference)
        text_to_check = desc + " " + bill_ref
        
        # 1. Infer from Description or Bill Reference (Highest Priority)
        # Note: Using specific casing based on User preference/Screenshot
        if 'AUH' in text_to_check or 'ABU DHABI' in text_to_check:
            return 'ABUDHABI'
        elif 'SHJ' in text_to_check or 'SHARJAH' in text_to_check or 'FAIZ' in text_to_check:
            return 'Sharjah'
        elif 'DXB' in text_to_check or 'DUBAI' in text_to_check:
            return 'Dubai'
        elif 'AJM' in text_to_check or 'AJMAN' in text_to_check:
            return 'Ajman'
        elif 'RAK' in text_to_check or 'RAS' in text_to_check:
            return 'Ras Al Khaimah'
        elif 'FUJ' in text_to_check or 'FUJAIRAH' in text_to_check:
            return 'Fujairah'
        elif 'UAQ' in text_to_check or 'UMM' in text_to_check:
            return 'Umm Al Quwain'

        # 2. If valid FP exists (not empty/NaN/Non-UAE), keep it
        if s_fp and 'Non-UAE' not in s_fp and s_fp.lower() != 'nan':
            return fp

        # 3. Default fallback
        return 'ABUDHABI'

    changes = 0
    for idx, row in df.iterrows():
        if pd.notna(row['Number']):
            original = row['Fiscal Position']
            new_val = fix_header_fp(row)
            if original != new_val:
                df.at[idx, 'Fiscal Position'] = new_val
                changes += 1

    print(f"Updated {changes} header rows based on Description or default.")

    # 3. Fix Journal Mapping
    print("Applying Journal Mapping...")
    journal_mapping = {
        'Mysore Restaurant': 'Purchases MS',
        'Envor': 'Purchases EV',
        # 'BOSS FAMILY': 'Purchases BF', # Assuming 'BOSS FAMILY' needs matching, might be sensitive to case/spacing. 
        # Checking user provided image keys.
        'ABU DHABI': 'Purchases AUH',
        'RAS AL KHAIMAH': 'Purchases RAK',
        'DUBAI': 'Purchases DXB',
        'SHARJAH': 'Purchases SHJ',
        'AJMAN': 'Purchases AJM',
        'FUJAIRAH': 'Purchases FUJ',
        'DUBAI STORE': 'Purchases DS'
    }
    
    # Adding naive matches for BOSS FAMILY if exact string differs slightly (e.g. extra spaces)
    # The export usually produces sanitized names.
    
    journal_changes = 0
    
    def get_journal_name(row):
        company = str(row.get('Company', '')).strip()
        
        # Exact match check
        if company in journal_mapping:
            return journal_mapping[company]
            
        # Partial/Case-insensitive fallbacks
        comp_upper = company.upper()
        if 'MYSORE' in comp_upper: return 'Purchases MS'
        if 'ENVOR' in comp_upper: return 'Purchases EV'
        if 'BOSS' in comp_upper: return 'Purchases BF'
        if 'ABU DHABI' in comp_upper: return 'Purchases AUH'
        if 'RAS' in comp_upper and 'KHAIMAH' in comp_upper: return 'Purchases RAK'
        if 'DUBAI STORE' in comp_upper: return 'Purchases DS' # Check before DUBAI
        if 'DUBAI' in comp_upper: return 'Purchases DXB'
        if 'SHARJAH' in comp_upper: return 'Purchases SHJ'
        if 'AJMAN' in comp_upper: return 'Purchases AJM'
        if 'FUJAIRAH' in comp_upper: return 'Purchases FUJ'
        
        return row.get('Journal*') # Return original if no match found

    for idx, row in df.iterrows():
        # Only update if current journal is 'Vendor Bills' or we want to force update. 
        # Requirement: "replace the 'Vendor Bills'..."
        # But safest is to ensure it matches company.
        
        # Only update header rows (where Company dictates the journal for the bill)
        if pd.isna(row.get('Number')):
             continue

        original_journal = row.get('Journal*')
        new_journal = get_journal_name(row)
        
        if new_journal and new_journal != original_journal:
             df.at[idx, 'Journal*'] = new_journal
             journal_changes += 1

    print(f"Updated {journal_changes} Journal entries.")

    print(f"Saving to {file_path}...")
    try:
        df.to_excel(file_path, index=False)
        print("Success! File updated.")
    except Exception as e:
        print(f"Failed to save file: {e}")

if __name__ == '__main__':
    main()
