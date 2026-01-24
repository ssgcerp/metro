
import pandas as pd
import os

output_dir = r'e:\odoo modules\19\metro\odoo14_to_19_migration\Export'
target_bill = "BILL/2025/12/0081"
files_to_check = ["VendorBills_RAS AL KHAIMAH.xlsx", "VendorBills_Ras Al-Khaima.xlsx"]

print(f"Checking for {target_bill} in output files...")

for fname in files_to_check:
    fpath = os.path.join(output_dir, fname)
    if os.path.exists(fpath):
        print(f"\nScanning {fname}...")
        try:
            df = pd.read_excel(fpath)
            # Check in 'Number' column
            matches = df[df['Number'] == target_bill]
            if not matches.empty:
                print(f"FOUND {len(matches)} rows in {fname}!")
                print(matches[['Number', 'Company', 'Invoice Bill Date']])
            else:
                print(f"Not found in {fname}.")
        except Exception as e:
            print(f"Error reading {fname}: {e}")
    else:
        print(f"File {fname} does not exist.")
