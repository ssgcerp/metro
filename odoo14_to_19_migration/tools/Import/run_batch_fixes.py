
import subprocess
import sys

FIX_SCRIPT = r"e:\odoo modules\19\metro\odoo14_to_19_migration\tools\Import\fix_bill_company.py"

# (Source, Target, [Bills])
MOVES = [
    ('ABU DHABI', 'AJMAN', ['EXP/2025/05/0037']),
    ('ABU DHABI', 'DUBAI', ['BILL/2025/07/0071', 'EXP/2025/12/0031']),
    ('ABU DHABI', 'FUJAIRAH', ['EXP/2025/02/0180', 'EXP/2025/05/0209']),
    ('SHARJAH', 'FUJAIRAH', ['SI-550100035553']),
    ('ABU DHABI', 'RAS AL KHAIMAH', ['EXP/2025/07/0063']),
    ('ABU DHABI', 'SHARJAH', ['BILL/2025/09/0001']),
    ('SHARJAH', 'ABU DHABI', ['BILL/2025/11/0053', 'EXP/2025/10/0038']),
]

def main():
    print("Starting Batch Fixes...")
    
    for src, dst, bills in MOVES:
        bill_str = ",".join(bills)
        print(f"\n[BATCH] Moving {len(bills)} bills from '{src}' to '{dst}'...")
        
        cmd = [
            "python", FIX_SCRIPT,
            "--url", "https://metro.equdaierp.com",
            "--db", "metrodb",
            "--user", "admin",
            "--password", "Amaze@321",
            "--old-company", src,
            "--new-company", dst,
            "--bills", bill_str
        ]
        
        try:
            subprocess.run(cmd, check=True)
            print("[BATCH] Success.")
        except subprocess.CalledProcessError as e:
            print(f"[BATCH] FAILED for {dst}: {e}")
            # We continue to try others
            
    print("\nBatch Fixes Completed.")

if __name__ == "__main__":
    main()
