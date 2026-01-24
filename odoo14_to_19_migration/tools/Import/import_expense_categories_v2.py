import xmlrpc.client
import pandas as pd
import time

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

FILE_PATH = r'e:\odoo modules\19\metro\odoo14_to_19_migration\expense COA.xlsx'

def connect():
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    return uid, models

def main():
    print("Reading Excel...")
    try:
        df = pd.read_excel(FILE_PATH)
    except Exception as e:
        print(f"Failed to read Excel: {e}")
        return

    # Analyze duplicates
    # Identify categories that appear more than once
    grouped = df.groupby('CATEGORY').size()
    duplicates = grouped[grouped > 1].index.tolist()
    print(f"Found {len(duplicates)} duplicate categories. They will be renamed.")

    uid, models = connect()
    print("Connected to Odoo.")

    # 1. Get all companies
    companies = models.execute_kw(DB, uid, PASS, 'res.company', 'search_read', [[]], {'fields': ['id', 'name']})
    print(f"Found {len(companies)} companies.")

    # 2. Iterate Excel rows
    for index, row in df.iterrows():
        category_name = str(row['CATEGORY']).strip()
        account_code = str(row['Code']).strip()
        account_name = str(row['Account Name']).strip()
        
        # Clean account code if it has decimals
        if account_code.endswith('.0'):
            account_code = account_code[:-2]
        
        # Determine Product Name
        if category_name in duplicates:
            final_name = f"{category_name} - {account_name}"
        else:
            final_name = category_name

        print(f"\nProcessing '{final_name}' (Code: {account_code})")

        # 3. Find or Create Product (Expense Category)
        # Search by name first
        product_domain = [('name', '=', final_name), ('can_be_expensed', '=', True)]
        product_ids = models.execute_kw(DB, uid, PASS, 'product.template', 'search', [product_domain])
        
        if product_ids:
            product_id = product_ids[0]
            print(f"  - Update existing Product ID: {product_id}")
        else:
            # Create new
            vals = {
                'name': final_name,
                'can_be_expensed': True,
                'type': 'service', # usually service
                'purchase_ok': False,
                'sale_ok': False,
            }
            product_id = models.execute_kw(DB, uid, PASS, 'product.template', 'create', [vals])
            print(f"  - Created new Product ID: {product_id}")

        # 4. Map Account for EACH Company
        for company in companies:
            comp_id = company['id']
            comp_name = company['name']
            
            # Find Account ID for this company and code
            # In Odoo 19, account.account uses company_ids (Many2many)
            acc_domain = [('code', '=', account_code), ('company_ids', 'in', [comp_id])]
            account_ids = models.execute_kw(DB, uid, PASS, 'account.account', 'search', [acc_domain])
            
            if account_ids:
                acc_id = account_ids[0]
                # Write company-dependent field
                models.execute_kw(DB, uid, PASS, 'product.template', 'write', [[product_id], {
                    'property_account_expense_id': acc_id
                }], {'context': {'company_id': comp_id}})
                # print(f"    - [{comp_name}] Linked Account {account_code}")
            else:
                # print(f"    - [{comp_name}] WARNING: Account {account_code} NOT FOUND.")
                pass

    print("\nDone.")

if __name__ == "__main__":
    main()
