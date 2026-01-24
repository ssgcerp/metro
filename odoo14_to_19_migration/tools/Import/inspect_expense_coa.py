import pandas as pd

file_path = r'e:\odoo modules\19\metro\odoo14_to_19_migration\expense COA.xlsx'
try:
    df = pd.read_excel(file_path)
    print("Columns:", df.columns.tolist())
    print("\nFirst 5 rows:")
    for index, row in df.head().iterrows():
        print(row.to_dict())
except Exception as e:
    print(f"Error reading excel: {e}")
