
import xmlrpc.client
import ssl

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

print(f"Connecting to {url}...")
common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url), context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url), context=ssl._create_unverified_context())

# Replication Context
all_companies = models.execute_kw(db, uid, password, 'res.company', 'search_read', [[], ['id', 'name']])
all_company_ids = [c['id'] for c in all_companies]
print(f"Using allowed_company_ids: {all_company_ids}")
ctx = {'allowed_company_ids': all_company_ids}

print("Connected. Searching for bill...")
bill_name = "BILL/2025/02/0052"
bills = models.execute_kw(db, uid, password, 'account.move', 'search_read', [[['name', '=', bill_name]]], {'fields': ['id', 'name', 'state', 'line_ids', 'company_id'], 'context': ctx})

if not bills:
    print("Bill not found!")
    exit()

bill = bills[0]
line_ids = bill['line_ids']
lines = models.execute_kw(db, uid, password, 'account.move.line', 'read', [line_ids], {'fields': ['id', 'name', 'account_id', 'debit', 'credit', 'date_maturity', 'tax_ids', 'tax_line_id', 'tax_repartition_line_id'], 'context': ctx})

with open("inspect_result.txt", "w", encoding="utf-8") as f:
    f.write(f"Found Bill: {bill['name']} (ID: {bill['id']}, State: {bill['state']}, Company: {bill['company_id']})\n")
    f.write(f"Processing {len(line_ids)} lines...\n")
    f.write("-" * 140 + "\n")
    f.write(f"{'ID':<10} | {'ACC_ID':<8} | {'Account':<40} | {'Type':<20} | {'Debit':<10} | {'Credit':<10} | {'Date Mat.':<15} | {'Tax Rep/Line'}\n")
    f.write("-" * 140 + "\n")

    for line in lines:
        acc_id = line['account_id'][0] if line['account_id'] else False
        acc_name = line['account_id'][1] if line['account_id'] else "No Account"
        
        acc_type = 'N/A'
        if acc_id:
            # Fetch Account Info
            acc = models.execute_kw(db, uid, password, 'account.account', 'read', [[acc_id]], {'fields': ['code', 'account_type']})
            if acc:
                acc_type = acc[0].get('account_type', 'N/A')
        
        tax_info = "None"
        if line.get('tax_line_id'): tax_info = f"TaxLine: {line['tax_line_id']}"
        if line.get('tax_repartition_line_id'): tax_info = f"RepLine: {line['tax_repartition_line_id']}"
        
        f.write(f"{line['id']:<10} | {str(acc_id):<8} | {acc_name[:40]:<40} | {acc_type:<20} | {line['debit']:<10} | {line['credit']:<10} | {str(line['date_maturity']):<15} | {tax_info}\n")

    f.write("-" * 140 + "\n")
print("Done writing to inspect_result.txt")
