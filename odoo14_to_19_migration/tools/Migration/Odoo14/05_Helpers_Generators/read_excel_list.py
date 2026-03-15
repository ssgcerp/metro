import pandas as pd
file_path = r"e:\odoo modules\19\metro\odoo14_to_19_migration\tools\Docs\Payments (account.payment) (1).xlsx"
df = pd.read_excel(file_path)
print(f"Total rows in Excel: {len(df)}")
print(f"Unique numbers: {df['Number'].nunique()}")
print(df['Number'].head(10).tolist())
