import pandas as pd

FILE_PATH = r'e:\odoo modules\19\metro\odoo14_to_19_migration\expense COA.xlsx'

def main():
    try:
        df = pd.read_excel(FILE_PATH)
        # Check row with Code 400909
        # Convert code to string to be safe
        df['Code'] = df['Code'].astype(str)
        row = df[df['Code'] == '400909']
        print("Row with Code 400909:")
        print(row.to_dict(orient='records'))

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
