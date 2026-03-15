"""Diagnose bill matching via vendor.bill.migration.line and check migrated bill lines."""
import xmlrpc.client

# Odoo 18
URL18 = "https://metro-fire-system-llc.odoo.com"
DB18  = "metro-fire-system-llc"
U18   = "sruthi@metrofiresystems.com"
P18   = "Sruthi@321"

# Odoo 19
URL19 = "https://metro.equdaierp.com"
DB19  = "metrodb"
U19   = "admin"
P19   = "Amaze@321"

s18 = xmlrpc.client.ServerProxy(URL18 + "/xmlrpc/2/object")
uid18 = xmlrpc.client.ServerProxy(URL18 + "/xmlrpc/2/common").authenticate(DB18, U18, P18, {})

s19 = xmlrpc.client.ServerProxy(URL19 + "/xmlrpc/2/object")
uid19 = xmlrpc.client.ServerProxy(URL19 + "/xmlrpc/2/common").authenticate(DB19, U19, P19, {})

print("Connected: Odoo18 uid=%s, Odoo19 uid=%s" % (uid18, uid19))

# Fetch migrated vendor bills from vendor.bill.migration.line  
migration_lines = s19.execute_kw(DB19, uid19, P19, "vendor.bill.migration.line", "search_read",
    [[("status", "=", "migrated")]],
    {"fields": ["id", "uploaded_bill_number", "odoo19_move_id", "status"], "limit": 5})

print("\nMigration lines (status=migrated, limit=5):")
for ml in migration_lines:
    print("  ML %s | bill_number=%s | odoo19_move_id=%s" % (
        ml["id"], ml.get("uploaded_bill_number"), ml.get("odoo19_move_id")))

# Try reading a specific migrated bill in Odoo 19
if migration_lines:
    ml = migration_lines[0]
    move_id_raw = ml.get("odoo19_move_id")
    bill_number = ml.get("uploaded_bill_number")
    
    if move_id_raw:
        move_id = move_id_raw[0] if isinstance(move_id_raw, list) else move_id_raw
        bill19 = s19.execute_kw(DB19, uid19, P19, "account.move", "search_read",
            [[("id", "=", move_id)]],
            {"fields": ["id", "name", "invoice_line_ids", "company_id"], "limit": 1})
        if bill19:
            b19 = bill19[0]
            print("\nOdoo19 bill %s (ID=%s, Company=%s):" % (b19["name"], b19["id"], b19["company_id"]))
            lines19 = s19.execute_kw(DB19, uid19, P19, "account.move.line", "search_read",
                [[("id", "in", b19["invoice_line_ids"]), ("display_type", "=", False), ("tax_line_id", "=", False)]],
                {"fields": ["id", "name", "account_id", "analytic_distribution", "product_id"]})
            for l in lines19:
                print("  Line %s | prod=%s | account=%s | analytic=%s" % (
                    l["id"], l.get("product_id"), l["account_id"], l.get("analytic_distribution") or ""))
    
    if bill_number:
        # Find in Odoo 18 by bill number
        bills18 = s18.execute_kw(DB18, uid18, P18, "account.move", "search_read",
            [[("name", "=", bill_number), ("move_type", "=", "in_invoice")]],
            {"fields": ["id", "name", "invoice_line_ids"], "limit": 1})
        if bills18:
            b18 = bills18[0]
            print("\nOdoo18 bill %s (ID=%s):" % (b18["name"], b18["id"]))
            lines18 = s18.execute_kw(DB18, uid18, P18, "account.move.line", "search_read",
                [[("id", "in", b18["invoice_line_ids"]), ("display_type", "=", False), ("tax_line_id", "=", False)]],
                {"fields": ["id", "name", "account_id", "analytic_distribution", "product_id"]})
            for l in lines18:
                print("  Line %s | prod=%s | account=%s | analytic=%s" % (
                    l["id"], l.get("product_id"), l["account_id"], l.get("analytic_distribution") or ""))
        else:
            print("No Odoo 18 match for bill number:", bill_number)

print("\nDone.")
