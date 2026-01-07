import pandas as pd
import sys

file_path = r'e:\odoo modules\19\metro\odoo14_to_19_migration\Invoices format.xlsx'

try:
    # Read the first few rows
    df = pd.read_excel(file_path, nrows=5)
    
    print("Columns:")
    print(df.columns.tolist())
    print("\nFirst 5 rows:")
    print(df.to_string())

except Exception as e:
    print(f"Error reading excel: {e}")
