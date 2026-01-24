
import pandas as pd

file_path = r"e:\odoo modules\19\metro\odoo14_to_19_migration\Export\VendorPayments_Export.xlsx"

try:
    df = pd.read_excel(file_path)
    print("Columns:", df.columns.tolist())
    
    if 'State' in df.columns:
        print("\nUnique values in 'State' column:")
        print(df['State'].unique())
        print("\nValue Counts:")
        print(df['State'].value_counts())
    else:
        print("'State' column not found.")
        
except Exception as e:
    print(f"Error: {e}")
