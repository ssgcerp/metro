import pandas as pd

file_path = r'e:\odoo modules\19\metro\odoo14_to_19_migration\expense COA.xlsx'
try:
    df = pd.read_excel(file_path)
    total_rows = len(df)
    unique_categories = df['CATEGORY'].nunique()
    
    print(f"Total Rows: {total_rows}")
    print(f"Unique Categories: {unique_categories}")
    
    print("\nDuplicate Categories:")
    counts = df['CATEGORY'].value_counts()
    for name, count in counts.items():
        if count > 1:
            print(f"- '{name}': {count} occurrences")
            
except Exception as e:
    print(f"Error reading excel: {e}")
