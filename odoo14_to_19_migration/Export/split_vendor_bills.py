
import pandas as pd
import os
import re

# File path
file_path = r'e:\odoo modules\19\metro\odoo14_to_19_migration\Export\Odoo18_VendorBills_Metro_Fire_System_LLC_20260109_111059.xlsx'
output_dir = r'e:\odoo modules\19\metro\odoo14_to_19_migration\Export'

def sanitize_filename(name):
    # Remove invalid characters for filenames
    return re.sub(r'[\\/*?:"<>|]', "", str(name))

def split_excel_by_company():
    print(f"Reading file: {file_path}")
    try:
        # Read the Excel file
        df = pd.read_excel(file_path)
        
        # Check if 'Company' column exists
        if 'Company' not in df.columns:
            print("Error: 'Company' column not found in the Excel file.")
            print(f"Available columns: {df.columns.tolist()}")
            return

        # Get unique companies
        # Forward fill the 'Company' column to handle multi-line bills
        df['Company'] = df['Company'].ffill()

        # Normalize company names
        # Defines mapping for specific corrections
        normalization_map = {
            'RAS AL-KHAIMA': 'RAS AL KHAIMAH',
            'UMM AL QUWAIN': 'UMM AL QUWAIN', # Ensure consistent casing if needed, but upper() handles it
        }

        def normalize_name(name):
            if pd.isna(name):
                return name
            # Convert to string, strip whitespace, and convert to uppercase
            name = str(name).strip().upper()
            # Apply manual mapping if exists
            return normalization_map.get(name, name)

        df['Company'] = df['Company'].apply(normalize_name)

        companies = df['Company'].unique()
        print(f"Found {len(companies)} companies: {companies}")

        for company in companies:
            if pd.isna(company):
                continue
                
            clean_company_name = sanitize_filename(company)
            company_df = df[df['Company'] == company]
            
            output_filename = f"VendorBills_{clean_company_name}.xlsx"
            output_path = os.path.join(output_dir, output_filename)
            
            print(f"Saving {len(company_df)} rows for '{company}' to {output_filename}...")
            company_df.to_excel(output_path, index=False)
            
        print("Success! All files created.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    split_excel_by_company()
