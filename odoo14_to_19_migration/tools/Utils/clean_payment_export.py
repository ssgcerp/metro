
import xmlrpc.client
import pandas as pd
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description='Remove existing payments from Excel')
    parser.add_argument('--url', required=True, help='Odoo URL')
    parser.add_argument('--db', required=True, help='Odoo DB')
    parser.add_argument('--user', required=True, help='Odoo User')
    parser.add_argument('--password', required=True, help='Odoo Password')
    parser.add_argument('--file', required=True, help='Excel File Path')
    
    args = parser.parse_args()
    
    print(f"\nScanning Odoo for existing payments...")
    
    try:
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(args.url))
        uid = common.authenticate(args.db, args.user, args.password, {})
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(args.url))
        
        # Load Excel
        print(f"Loading Excel: {args.file}")
        df = pd.read_excel(args.file)
        initial_count = len(df)
        print(f"Total Rows in Excel: {initial_count}")
        
        # Get all Payment Names from Excel
        excel_pay_nums = df['Payment Number'].astype(str).str.strip().tolist()
        # Remove nan or empty
        excel_pay_nums = [n for n in excel_pay_nums if n and n.lower() != 'nan']
        
        # Search Odoo for these names 
        # (Chunking if too large? 4000 is okay for one domain usually, but lets match 'name' in list)
        
        print("Checking existence in Odoo...")
        # We fetch only names that match
        existing_names = set()
        
        # Chunking just in case of URL length limits (though XMLRPC usually handles it)
        chunk_size = 1000
        for i in range(0, len(excel_pay_nums), chunk_size):
            chunk = excel_pay_nums[i:i+chunk_size]
            existing_recs = models.execute_kw(args.db, uid, args.password,
                'account.payment', 'search_read',
                [[('name', 'in', chunk)]],
                {'fields': ['name']})
            
            for r in existing_recs:
                existing_names.add(r['name'])
                
        print(f"Found {len(existing_names)} payments already in Odoo.")
        
        # Filter DataFrame
        # Keep rows where 'Payment Number' is NOT in existing_names
        df_clean = df[~df['Payment Number'].astype(str).str.strip().isin(existing_names)]
        
        final_count = len(df_clean)
        removed_count = initial_count - final_count
        
        print(f"Removed: {removed_count}")
        print(f"Remaining: {final_count}")
        
        if removed_count > 0:
            df_clean.to_excel(args.file, index=False)
            print(f"Successfully updated {args.file}")
        else:
            print("No payments removed (nothing matched). File unchanged.")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
