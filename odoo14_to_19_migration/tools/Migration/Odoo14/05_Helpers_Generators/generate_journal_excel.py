import xmlrpc.client
import ssl
import pandas as pd
import argparse

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

def main():
    parser = argparse.ArgumentParser(description='Generate Journal Mapping Excel')
    parser.add_argument('--company', help='Filter by company name')
    parser.add_argument('--output', default='journal_mapping_template.xlsx', help='Output Excel filename')
    args = parser.parse_args()

    print(f"Connecting to Odoo at {url}...")
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
        uid = common.authenticate(db, username, password, {})
        if not uid:
            print("Authentication failed.")
            return

        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

        print(f"Fetching inbound payments{' for ' + args.company if args.company else ''}...")
        domain = [('payment_type', '=', 'inbound')]
        if args.company:
            domain.append(('company_id.name', '=', args.company))

        payments = models.execute_kw(db, uid, password, 'account.payment', 'search_read', 
            [domain], 
            {'fields': ['journal_id', 'company_id']})

        print(f"Total payments fetched: {len(payments)}")

        if not payments:
            print("No payment data found to generate Excel file.")
            return

        # Aggregate data: count payments per (company, journal)
        journal_counts = {}

        for p in payments:
            if p.get('company_id') and p.get('journal_id'):
                company_name = p['company_id'][1]
                journal_id = p['journal_id'][0]
                journal_name = p['journal_id'][1]
                
                key = (company_name, journal_name)
                if key not in journal_counts:
                    journal_counts[key] = {
                        'Source Journal ID': journal_id,
                        'Source Journal Name': journal_name,
                        'Source Company': company_name,
                        'Total No. of Payments': 0,
                        'Dest Journal ID': '',
                        'Dest Journal Name': '',
                        'Dest Company': '',
                        'Parent Company': ''
                    }
                journal_counts[key]['Total No. of Payments'] += 1

        # Prepare data for Excel
        data = list(journal_counts.values())

        if data:
            df = pd.DataFrame(data)
            df = df.sort_values(by=['Source Company', 'Source Journal Name'])

            # Reorder columns as requested
            columns_order = [
                'Source Journal ID',
                'Source Journal Name',
                'Source Company',
                'Total No. of Payments',
                'Dest Journal ID',
                'Dest Journal Name',
                'Dest Company',
                'Parent Company'
            ]
            df = df[columns_order]

            # Export to Excel
            excel_file = args.output
            df.to_excel(excel_file, index=False)
            print(f"Successfully generated {excel_file} with {len(df)} mapped journals.")
        else:
            print("No consolidated data to export.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
