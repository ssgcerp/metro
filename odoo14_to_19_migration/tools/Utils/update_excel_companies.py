
import pandas as pd
import re
import sys
import os

FILE_PATH = r"e:\odoo modules\19\metro\odoo14_to_19_migration\Export\Odoo18_vendorbills.xlsx"

def infer_company(text):
    if not isinstance(text, str):
        text = str(text) if text else ""
    text = text.upper()
    
    if 'SHJ' in text or 'SHARJAH' in text:
        return 'SHARJAH'
    if 'DXB' in text or 'DUBAI' in text:
        return 'DUBAI'
    if 'AUH' in text or 'ABU DHABI' in text or 'MUSAFFAH' in text:
        return 'ABU DHABI'
    if 'AJM' in text or 'AJMAN' in text:
        return 'AJMAN'
    if 'FUJ' in text or 'FUJAIRAH' in text:
        return 'FUJAIRAH'
    if 'RAK' in text or 'RAS' in text or 'KHAIMAH' in text:
        return 'RAS AL KHAIMAH'  # Or RAS AL KHAIMAH
    if 'ENVOR' in text or 'EV' in text.split('/'): # be careful with EV
        return 'Envor'
    if 'BOSS' in text or 'BF' in text.split('/'):
        return 'BOSS FAMILY'
    if 'MYSORE' in text or 'MS' in text.split('/'):
        return 'Mysore Restaurant'
    if 'DS' in text.split('/'):
        return 'DUBAI STORE'
        
    return None

def main():
    if not os.path.exists(FILE_PATH):
        print(f"File not found: {FILE_PATH}")
        sys.exit(1)
        
    print(f"Reading {FILE_PATH}...")
    try:
        df = pd.read_excel(FILE_PATH)
        
        # Determine source column for inference
        # Priority: Bill Reference -> Number -> Payment Reference
        
        updates = 0
        
        for index, row in df.iterrows():
            # Get current company
            curr_comp = str(row.get('Company', '')).strip()
            
            # Infer from Bill Reference
            ref = str(row.get('Bill Reference', ''))
            new_comp = infer_company(ref)
            
            if not new_comp:
                # Try Number
                num = str(row.get('Number', ''))
                new_comp = infer_company(num)
                
            if not new_comp:
                # Try payment ref
                pay_ref = str(row.get('Payment Reference', ''))
                new_comp = infer_company(pay_ref)
            
            if new_comp and new_comp.upper() != curr_comp.upper():
                df.at[index, 'Company'] = new_comp
                updates += 1
                # print(f"Row {index}: mapped '{ref}'/'{num}' -> {new_comp}")
        
        print(f"Updated {updates} rows with inferred company names.")
        
        output_path = FILE_PATH.replace('.xlsx', '_Updated.xlsx')
        df.to_excel(output_path, index=False)
        print(f"Saved updated file to: {output_path}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
