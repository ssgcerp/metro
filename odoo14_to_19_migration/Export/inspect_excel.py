
import pandas as pd

file_path = r'e:\odoo modules\19\metro\odoo14_to_19_migration\Export\Odoo18_VendorBills_Metro_Fire_System_LLC_20260109_111059.xlsx'
try:
    df = pd.read_excel(file_path, nrows=5)
    print("Columns List:")
    for col in df.columns:
        print(col)
except Exception as e:
    print("Error:", e)
