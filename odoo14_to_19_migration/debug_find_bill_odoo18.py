
import xmlrpc.client
import sys

URL = "https://metro-fire-system-llc.odoo.com"
DB = "metro-fire-system-llc"
USER = "sruthi@metrofiresystems.com"
PASS = "Sruthi@321"

TARGET = "EXP/2025/10/0038"

def main():
    print(f"Connecting to {URL}...")
    try:
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL))
        uid = common.authenticate(DB, USER, PASS, {})
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL))
        
        print(f"Searching for '{TARGET}' in Odoo 18...")
        
        # 1. Search by Name
        print("1. Checking 'name' field...")
        res = models.execute_kw(DB, uid, PASS, 'account.move', 'search_read', [[('name', '=', TARGET)]], {'fields': ['name', 'state', 'ref', 'payment_reference']})
        if res:
             print(f"   -> FOUND in 'name'! Data: {res}")
        else:
             print("   -> Not found in 'name'.")
             
        # 2. Search by Ref
        print("2. Checking 'ref' field...")
        res = models.execute_kw(DB, uid, PASS, 'account.move', 'search_read', [[('ref', '=', TARGET)]], {'fields': ['name', 'state', 'ref', 'payment_reference']})
        if res:
             print(f"   -> FOUND in 'ref'! Data: {res}")
        else:
             print("   -> Not found in 'ref'.")

        # 3. Search by Payment Reference
        print("3. Checking 'payment_reference' field...")
        res = models.execute_kw(DB, uid, PASS, 'account.move', 'search_read', [[('payment_reference', '=', TARGET)]], {'fields': ['name', 'state', 'ref', 'payment_reference']})
        if res:
             print(f"   -> FOUND in 'payment_reference'! Data: {res}")
        else:
             print("   -> Not found in 'payment_reference'.")
             
        # 4. Search ILIKE (Broad search)
        print("4. Broad ILIKE search (name/ref)...")
        res = models.execute_kw(DB, uid, PASS, 'account.move', 'search_read', ['|', ('name', 'ilike', TARGET), ('ref', 'ilike', TARGET)], {'fields': ['name', 'state', 'ref', 'payment_reference']})
        if res:
             print(f"   -> FOUND via ILIKE! Data: {res}")
        else:
             print("   -> Not found via ILIKE.")


    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
