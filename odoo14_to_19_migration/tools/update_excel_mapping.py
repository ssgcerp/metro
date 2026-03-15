import pandas as pd

df = pd.read_excel(r'e:\odoo modules\19\metro\odoo14_to_19_migration\tools\journal_mapping_metrodb_to_newdb.xlsx')

# The user wants to map these specific cash journals to "Cash" in the newdb
cash_journals = [
    ("Cash", "CSH1", "ABU DHABI", "cash"),
    ("Cash", "CSH1", "DUBAI STORE", "cash"),
    ("Cash", "CSH1", "Envor", "cash"),
    ("Cash", "CSH2", "FUJAIRAH", "cash"),
    ("Cash", "CSH2", "DUBAI", "cash")
]

for idx, row in df.iterrows():
    if (row['Source Name (metrodb)'], row['Source Code'], row['Source Company'], row['Type']) in cash_journals:
        df.at[idx, 'Target Name (newdb)'] = 'Cash'
        df.at[idx, 'Mapping Status'] = 'Mapped via manual script'

df.to_excel(r'e:\odoo modules\19\metro\odoo14_to_19_migration\tools\journal_mapping_metrodb_to_newdb.xlsx', index=False)
print("Updated Excel file with manual mappings.")
