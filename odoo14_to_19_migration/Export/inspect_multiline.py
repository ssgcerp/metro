
import pandas as pd

file_path = r'e:\odoo modules\19\metro\odoo14_to_19_migration\Export\Odoo18_VendorBills_Metro_Fire_System_LLC_20260109_111059.xlsx'

try:
    df = pd.read_excel(file_path)
    print("Total rows:", len(df))
    print("Null Company values:", df['Company'].isna().sum())
    
    # Show rows where Company is NaN but maybe Number is not? or just show a chunk around a NaN company
    nan_company_rows = df[df['Company'].isna()]
    if not nan_company_rows.empty:
        print("\nFirst 5 rows with missing Company:")
        print(nan_company_rows.head(5)[['Number', 'Company', 'Description']])
        
        # Checking context of the first NaN occurrence
        first_nan_index = nan_company_rows.index[0]
        start_idx = max(0, first_nan_index - 2)
        end_idx = min(len(df), first_nan_index + 3)
        print(f"\nContext around row {first_nan_index} (rows {start_idx} to {end_idx}):")
        print(df.iloc[start_idx:end_idx][['Number', 'Company', 'Description']])
    else:
        print("\nNo rows with missing 'Company' found. Checking for duplicate Numbers with different companies?")
        
except Exception as e:
    print(f"Error: {e}")
