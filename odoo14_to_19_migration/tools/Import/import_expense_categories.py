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

    uid, models = connect()
    print("Connected to Odoo.")

    # 1. Get all companies
    companies = models.execute_kw(DB, uid, PASS, 'res.company', 'search_read', [[]], {'fields': ['id', 'name']})
    print(f"Found {len(companies)} companies.")

    # 2. Iterate Excel rows
    for index, row in df.iterrows():
        category_name = str(row['CATEGORY']).strip()
        account_code = str(row['Code']).strip()
        # Clean account code if it has decimals (e.g. 123.0 -> 123)
        if account_code.endswith('.0'):
            account_code = account_code[:-2]
            
        print(f"\nProcessing '{category_name}' (Account Code: {account_code})")

        # 3. Find or Create Product (Expense Category)
        # Search by name first
        product_domain = [('name', '=', category_name), ('can_be_expensed', '=', True)]
        product_ids = models.execute_kw(DB, uid, PASS, 'product.template', 'search', [product_domain])
        
        if product_ids:
            product_id = product_ids[0]
            print(f"  - Update existing Product ID: {product_id}")
        else:
            # Create new
            vals = {
                'name': category_name,
                'can_be_expensed': True,
                'type': 'service', # Usually expenses are services
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
                # IMPORTANT: Use context to specify which company we are writing for
                models.execute_kw(DB, uid, PASS, 'product.template', 'write', [[product_id], {
                    'property_account_expense_id': acc_id
                }], {'context': {'company_id': comp_id}})
                print(f"    - [{comp_name}] Linked Account {account_code} (ID: {acc_id})")
            else:
                print(f"    - [{comp_name}] WARNING: Account {account_code} NOT FOUND.")

    print("\nDone.")

if __name__ == "__main__":
    main()
