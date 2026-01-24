import pandas as pd

FILE_PATH = r'e:\odoo modules\19\metro\odoo14_to_19_migration\expense COA.xlsx'

def main():
    try:
        df = pd.read_excel(FILE_PATH)
        
        # Group by Category and list unique Codes
        grouped = df.groupby('CATEGORY')['Code'].nunique()
        
        print("Categories with multiple distinct Account Codes:")
        multi_code = grouped[grouped > 1]
        for cat, count in multi_code.items():
            print(f"- {cat}: {count} unique codes")
            
            # Show examples
            examples = df[df['CATEGORY'] == cat][['Code', 'Account Name']].head(3)
            print(examples.to_string(index=False, header=False))
            print()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
