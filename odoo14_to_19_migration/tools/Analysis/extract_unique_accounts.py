import pandas as pd
import os
import sys

def main():
    # Identify Export Dir
    # Script is in tools/Analysis/
    # abspath -> tools/Analysis/script.py
    # dirname -> tools/Analysis
    # dirname -> tools
    # dirname -> migration
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    export_dir = os.path.join(base_dir, 'Export')

    if not os.path.exists(export_dir):
        print(f"Export directory not found: {export_dir}")
        return

    unique_accounts = set()
    
    files = [f for f in os.listdir(export_dir) if f.endswith('.xlsx') and not f.startswith('~$')]
    if not files:
        print("No Excel files found.")
        return

    print(f"Scanning {len(files)} files in {export_dir}...")

    for f in files:
        path = os.path.join(export_dir, f)
        print(f"Reading {f}...")
        try:
            df = pd.read_excel(path)
            if 'Invoice Lines/Account*' in df.columns:
                accounts = df['Invoice Lines/Account*'].dropna().unique()
                for acc in accounts:
                    clean_acc = str(acc).strip()
                    if clean_acc and clean_acc.lower() != 'nan':
                        unique_accounts.add(clean_acc)
        except Exception as e:
            print(f"Error reading {f}: {e}")

    # Sort
    sorted_accounts = sorted(list(unique_accounts))
    
    # Save to file
    out_file = os.path.join(export_dir, 'Unique_Accounts_List.txt')
    with open(out_file, 'w', encoding='utf-8') as f:
        for acc in sorted_accounts:
            f.write(f"{acc}\n")
            
    print(f"\nFound {len(sorted_accounts)} unique accounts.")
    print(f"Saved list to: {out_file}")

if __name__ == '__main__':
    main()
