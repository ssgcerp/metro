import xmlrpc.client
import ssl

def main():
    url = "https://erpmfs.com"
    db = "metro_production_8_8_22"
    username = "Sales.auh@metrofiresystems.com"
    password = "Sales@185734"

    print(f"Connecting to {url}...")
    
    context = ssl._create_unverified_context()
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=context)
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=context)
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("Authentication failed")
        return

    # Check for core fields only
    try:
        fields = models.execute_kw(db, uid, password, 'account.payment', 'fields_get', 
            ['name', 'amount', 'payment_type', 'partner_type', 'partner_id', 'journal_id', 'ref', 'communication', 'invoice_ids'], 
            {'attributes': ['string', 'type', 'relation']}
        )
        print("\nAvailable Core Fields:")
        for f, data in fields.items():
            print(f" - {f}: {data}")
    except Exception as e:
        print(f"Failed to inspect fields: {e}")
    
    # Fetch a sample payment
    print("\nFetching sample payment (Voucher 15186)...")
    
    # Try searching by name (likely the sequence number)
    try:
        payment_ids = models.execute_kw(db, uid, password, 'account.payment', 'search', [[('name', 'ilike', '15186')]], {'limit': 1})
    except Exception as e:
        print(f"Search by name failed: {e}")
        payment_ids = []

    if not payment_ids:
         try:
             # Try 'ref' if name failed
             payment_ids = models.execute_kw(db, uid, password, 'account.payment', 'search', [[('ref', 'ilike', '15186')]], {'limit': 1})
         except Exception as e:
            print(f"Search by ref failed: {e}")

    if not payment_ids:
        print("Sample 15186 not found, fetching any posted customer payment...")
        payment_ids = models.execute_kw(db, uid, password, 'account.payment', 'search', [[('payment_type', '=', 'inbound'), ('partner_type', '=', 'customer'), ('state', '=', 'posted')]], {'limit': 1})

    if payment_ids:
        payment = models.execute_kw(db, uid, password, 'account.payment', 'read', [payment_ids], [])[0]
        print("\nPayment Data:")
        for k, v in payment.items():
            print(f"{k}: {v}")
    else:
        print("No payments found.")

if __name__ == "__main__":
    main()
