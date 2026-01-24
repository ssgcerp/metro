
import pandas as pd

file_path = r'e:\odoo modules\19\metro\odoo14_to_19_migration\Export\Odoo18_VendorBills_Metro_Fire_System_LLC_20260109_111059.xlsx'

try:
    df = pd.read_excel(file_path)
    
    # helper to print full values
    pd.set_option('display.max_colwidth', None)
    
    # 1. Find the specific bill
    target_bill = "BILL/2025/12/0081"
    bill_rows = df[df['Number'] == target_bill]
    
    print(f"--- Searching for {target_bill} ---")
    if not bill_rows.empty:
        print(f"Found {len(bill_rows)} rows for {target_bill}:")
        print(bill_rows[['Number', 'Company', 'Partner', 'Invoice Bill Date']])
        company_val = bill_rows.iloc[0]['Company']
        print(f"RaW Company value: '{company_val}'")
        print(f"Bytes: {company_val.encode('utf-8') if isinstance(company_val, str) else 'Not a string'}")
    else:
        print(f"Bill {target_bill} NOT FOUND in 'Number' column.")
        
    # 2. List all unique companies to check for near-duplicates
    print("\n--- Unique Company Values ---")
    unique_companies = df['Company'].dropna().unique()
    for comp in unique_companies:
        print(f"'{comp}'")

except Exception as e:
    print(f"Error: {e}")
