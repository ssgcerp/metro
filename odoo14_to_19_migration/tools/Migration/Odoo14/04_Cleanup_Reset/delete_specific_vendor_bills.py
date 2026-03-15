import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

ctx = ssl._create_unverified_context()
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ctx, allow_none=True)
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ctx, allow_none=True)

# List provided by user (New Large Batch)
to_delete_names = [
    "BILL/2022/09/0001", "BILL/2022/10/0001", "BILL/2022/11/0013", "BILL/2022/11/0017",
    "BILL/2022/11/0007", "BILL/2022/11/0016", "BILL/2022/11/0018", "BILL/2022/11/0015",
    "BILL/2022/11/0006", "BILL/2022/11/0014", "BILL/2022/11/0001", "BILL/2022/11/0008",
    "BILL/2022/11/0009", "BILL/2022/11/0010", "BILL/2022/12/0005", "BILL/2022/12/0021",
    "BILL/2022/12/0012", "BILL/2022/12/0020", "BILL/2022/12/0004", "BILL/2022/12/0006",
    "BILL/2022/12/0008", "BILL/2022/12/0010", "BILL/2022/12/0013", "BILL/2022/12/0016",
    "BILL/2022/12/0019", "BILL/2022/12/0027", "BILL/2023/01/0006", "BILL/2023/01/0032",
    "BILL/2023/01/0008", "BILL/2023/01/0003", "BILL/2023/01/0022", "BILL/2023/01/0030",
    "BILL/2023/01/0005", "BILL/2023/01/0011", "BILL/2023/01/0016", "BILL/2023/01/0017",
    "BILL/2023/01/0021", "BILL/2023/01/0031", "BILL/2023/01/0041", "BILL/2023/01/0043",
    "BILL/2023/01/0044", "BILL/2023/02/0013", "BILL/2023/02/0031", "BILL/2023/02/0010",
    "BILL/2023/02/0033", "BILL/2023/02/0027", "BILL/2023/02/0003", "BILL/2023/02/0006",
    "BILL/2023/02/0017", "BILL/2023/02/0015", "BILL/2023/02/0016", "BILL/2023/02/0022",
    "BILL/2023/02/0023", "BILL/2023/02/0024", "BILL/2023/02/0026", "BILL/2023/02/0028",
    "BILL/2023/02/0035", "BILL/2023/02/0039", "BILL/2023/02/0040", "BILL/2023/02/0048",
    "BILL/2023/02/0050", "BILL/2023/03/0003", "BILL/2023/03/0006", "BILL/2023/03/0007",
    "BILL/2023/03/0009", "BILL/2023/03/0012", "BILL/2023/03/0013", "BILL/2023/03/0014",
    "BILL/2023/03/0015", "BILL/2023/03/0011", "BILL/2023/03/0008", "BILL/2023/03/0018",
    "BILL/2023/03/0029", "BILL/2023/03/0032", "BILL/2023/03/0038", "BILL/2023/03/0047",
    "BILL/2023/03/0048", "BILL/2023/03/0049", "BILL/2023/03/0053", "BILL/2023/03/0054",
    "BILL/2023/03/0055", "BILL/2023/03/0057", "BILL/2023/04/0041", "BILL/2023/04/0044",
    "BILL/2023/04/0053", "BILL/2023/04/0002", "BILL/2023/04/0015", "BILL/2023/04/0005",
    "BILL/2023/04/0006", "BILL/2023/04/0008", "BILL/2023/04/0012", "BILL/2023/04/0016",
    "BILL/2023/04/0018", "BILL/2023/04/0019", "BILL/2023/04/0024", "BILL/2023/04/0026",
    "BILL/2023/04/0028", "BILL/2023/04/0048", "BILL/2023/04/0057", "BILL/2023/05/0030",
    "BILL/2023/05/0040", "BILL/2023/05/0042", "BILL/2023/05/0015", "BILL/2023/05/0013",
    "BILL/2023/05/0024", "BILL/2023/05/0002", "BILL/2023/04/0037-R1", "BILL/2023/05/0037",
    "BILL/2023/06/0031", "BILL/2023/06/0035", "BILL/2023/06/0002", "BILL/2023/06/0041",
    "BILL/2023/06/0042", "BILL/2023/06/0003", "BILL/2023/06/0008", "BILL/2023/06/0009",
    "BILL/2023/06/0022", "BILL/2023/06/0024", "BILL/2023/06/0025", "BILL/2023/06/0026",
    "BILL/2023/07/0001", "BILL/2023/07/0003", "BILL/2023/07/0010", "BILL/2023/07/0011",
    "BILL/2023/07/0012", "BILL/2023/07/0026", "BILL/2023/07/0031", "BILL/2023/07/0042",
    "BILL/2023/07/0029", "BILL/2023/07/0040", "BILL/2023/07/0045", "BILL/2023/07/0046",
    "BILL/2023/07/0027", "BILL/2023/07/0048", "BILL/2023/07/0049", "BILL/2023/07/0050",
    "BILL/2023/07/0051", "BILL/2023/08/0002", "BILL/2023/08/0021", "BILL/2023/08/0014",
    "BILL/2023/08/0020", "BILL/2023/08/0025", "BILL/2023/08/0008", "BILL/2023/08/0029",
    "BILL/2023/08/0037", "BILL/2023/08/0039", "BILL/2023/08/0040", "BILL/2023/08/0041",
    "BILL/2023/08/0042", "BILL/2023/08/0043", "BILL/2023/08/0044", "BILL/2023/08/0047",
    "BILL/2023/08/0048", "BILL/2023/08/0050", "BILL/2023/08/0051", "BILL/2023/08/0052",
    "BILL/2023/08/0053", "BILL/2023/08/0057", "BILL/2023/09/0007", "BILL/2023/09/0026",
    "BILL/2023/09/0028", "BILL/2023/09/0033", "BILL/2023/09/0044", "BILL/2023/09/0069",
    "BILL/2023/10/0002", "BILL/2023/10/0003", "BILL/2023/10/0005", "BILL/2023/10/0006",
    "BILL/2023/10/0015", "BILL/2023/10/0050", "BILL/2023/11/0005", "BILL/2023/11/0006",
    "BILL/2023/11/0016", "BILL/2023/11/0042", "BILL/2023/11/0050", "BILL/2023/11/0051",
    "BILL/2023/11/0064", "BILL/2023/11/0065", "BILL/2023/11/0066", "BILL/2023/12/0003",
    "BILL/2023/12/0004", "BILL/2023/12/0021", "BILL/2023/12/0026", "BILL/2023/12/0030",
    "BILL/2023/12/0035", "BILL/2023/12/0053", "BILL/2023/12/0061", "BILL/2023/12/0064",
    "BILL/2023/12/0065", "BILL/2024/01/0003", "BILL/2024/01/0004", "BILL/2024/01/0009",
    "BILL/2024/01/0011", "BILL/2024/01/0012", "BILL/2024/01/0017", "BILL/2024/01/0020",
    "BILL/2024/01/0021", "BILL/2024/01/0044", "BILL/2024/01/0048", "BILL/2024/01/0058",
    "BILL/2024/01/0061", "BILL/2024/01/0065", "BILL/2024/02/0015", "BILL/2024/02/0016",
    "BILL/2024/02/0020", "BILL/2024/02/0046", "BILL/2024/02/0048", "BILL/2024/02/0060",
    "BILL/2024/02/0064", "BILL/2024/02/0065", "BILL/2024/02/0075", "BILL/2024/02/0082",
    "BILL/2024/03/0007", "BILL/2024/03/0018", "BILL/2024/03/0019", "BILL/2024/03/0020",
    "BILL/2024/03/0030", "BILL/2024/03/0037", "BILL/2024/03/0054", "BILL/2024/04/0007",
    "BILL/2024/04/0021", "BILL/2024/04/0025", "BILL/2024/05/0008", "BILL/2024/05/0012",
    "BILL/2024/05/0015", "BILL/2024/05/0024", "BILL/2024/05/0043", "BILL/2024/05/0051",
    "BILL/2024/05/0058", "BILL/2024/05/0067", "BILL/2024/05/0070", "BILL/2024/05/0074",
    "BILL/2024/05/0076", "BILL/2024/05/0080", "BILL/2024/05/0083", "BILL/2024/06/081",
    "BILL/2024/06/0002", "BILL/2024/06/0012", "BILL/2024/06/0013", "BILL/2024/06/0032",
    "BILL/2024/06/0036", "BILL/2024/06/0043", "BILL/2024/06/0050", "BILL/2024/06/0052",
    "BILL/2024/06/0053", "BILL/2024/06/0058", "BILL/2024/07/0006", "BILL/2024/07/0009",
    "SI-550100034891", "SI-550100034914", "SI-550100034937", "SI-550100034947",
    "SI-550100034945", "SI-550100034939", "SI-550100034965", "SI-550100034959",
    "SI-550100034966", "SI-550100034970", "SI-550100034971", "SI-550100034988",
    "SI-550100035310", "SI-550100035001", "SI-550100034982", "SI-550100034986",
    "SI-550100034990", "SI-550100035010", "SI-550100035011", "SI-550100035014",
    "SI-550100035016", "SI-550100035018", "SI-550100035009", "SI-550100035012",
    "SI-550100035013", "SI-550100035015", "SI-550100035053", "SI-550100035004",
    "SI-550100035006", "SI-550100034999", "SI-550100035007", "SI-550100035035",
    "SI-550100035043", "SI-550100035049", "SI-550100035107", "SI-550100035045",
    "SI-550100035067", "SI-550100035073", "SI-550100035063", "SI-550100035101",
    "SI-550100035096", "SI-550100035089", "SI-550100035227", "SI-550100035244",
    "SI-550100035108", "SI-550100035170", "SI-550100035168", "SI-550100035173",
    "SI-550100035155", "SI-550100035195", "SI-550100035234", "SI-550100035238",
    "SI-550100035307", "SI-550100035212", "SI-550100035213", "SI-550100035293",
    "SI-550100035294", "SI-550100035295", "SI-550100035266", "SI-550100035254",
    "SI-550100035268", "SI-550100035269", "SI-550100035263", "SI-550100035264",
    "SI-550100035262", "SI-550100035255", "SI-550100035249", "SI-550100035311",
    "SI-550100035317", "SI-550100035431", "SI-550100035336", "SI-550100035345",
    "SI-550100035347", "SI-550100035495", "SI-550100035380", "SI-550100035381",
    "SI-550100035406", "SI-550100035407", "SI-550100035409", "SI-550100035419",
    "SI-550100035404", "SI-550100035399", "SI-550100035408", "SI-550100035392",
    "SI-550100035425", "SI-550100035488", "SI-550100035650", "SI-550100035453",
    "SI-550100035647", "SI-550100035648", "SI-550100035649", "SI-550100035474",
    "SI-550100035480", "SI-550100035487", "SI-550100035645", "SI-550100035646",
    "SI-550100035475", "SI-550100035471", "SI-550100035472", "SI-550100035473",
    "SI-550100035463", "SI-550100035477", "SI-550100035630", "SI-550100035464",
    "SI-550100035478", "SI-550100035643", "SI-550100035635", "SI-550100035639",
    "SI-550100035627", "SI-550100035507", "SI-550100035618", "SI-550100035536",
    "SI-550100035624", "SI-550100035530", "SI-550100035595", "SI-550100035598",
    "SI-550100035678", "SI-550100035684", "SI-550100035737", "SI-550100035725",
    "SI-550100035713", "SI-550100035694", "SI-550100035788", "SI-550100035771",
    "SI-550100035760", "SI-550100035749", "SI-550100035752", "SI-550100035763",
    "SI-550100035776", "SI-550100035806"
]

# Ensure unique
to_delete_names = list(set(to_delete_names))

print(f"Total unique bills to find and delete: {len(to_delete_names)}")

# Search for these bills
domain = [('move_type', '=', 'in_invoice'), ('name', 'in', to_delete_names)]
bills = models.execute_kw(db, uid, password, 'account.move', 'search_read', [domain], {'fields': ['id', 'name', 'state']})

print(f"Found {len(bills)} matching bills in Odoo 19.")

if not bills:
    print("Nothing to delete.")
    exit()

# Extract IDs and identify posted bills
bill_ids = [b['id'] for b in bills]
posted_ids = [b['id'] for b in bills if b['state'] == 'posted']

# Reset posted bills to draft
if posted_ids:
    print(f"Resetting {len(posted_ids)} posted bills to draft...")
    try:
        # Batch reset
        models.execute_kw(db, uid, password, 'account.move', 'button_draft', [posted_ids])
        print("  Bills reset to draft successfully.")
    except Exception as e:
        if 'marshal None' not in str(e):
             print(f"  Warning on batch draft reset: {e}. Attempting individual resets...")
             # Fallback to individual resets if batch fails (e.g. one specifically blocks)
             for pid in posted_ids:
                 try:
                     models.execute_kw(db, uid, password, 'account.move', 'button_draft', [[pid]])
                 except Exception as ex:
                      if 'marshal None' not in str(ex):
                          print(f"    Failed to reset ID {pid} to draft: {ex}")

# Final attempt to delete all items
print(f"Deleting {len(bill_ids)} bills...")
deleted_count = 0
# Unlink doesn't support batch well if one fails, so we can try batch first, then individual
try:
    models.execute_kw(db, uid, password, 'account.move', 'unlink', [bill_ids])
    deleted_count = len(bill_ids)
    print(f"Successfully deleted all {len(bill_ids)} bills in batch.")
except Exception as e:
    print(f"Batch deletion failed: {e}. Attempting individual deletions...")
    for bid in bill_ids:
        try:
            models.execute_kw(db, uid, password, 'account.move', 'unlink', [[bid]])
            deleted_count += 1
        except Exception as ex:
             print(f"  Failed to delete ID {bid}: {ex}")

print(f"\n--- Summary ---")
print(f"Total identified: {len(bills)}")
print(f"Successfully deleted: {deleted_count}")
print(f"Failed: {len(bills) - deleted_count}")
