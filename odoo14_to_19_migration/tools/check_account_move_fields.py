import xmlrpc.client
import ssl

def main():
    url = "https://metro.equdaierp.com"
    db = "metrodb"
    username = "admin"
    password = "Amaze@321"

    print(f"Connecting to {url}...")
    
    context = ssl._create_unverified_context()
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=context)
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=context)
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("Authentication failed")
        return

    # To check python attributes like _sequence_date_field, we typically can't access them via XML-RPC on the model class directly.
    # However, we can check if there are fields named 'move_line_ids'.
    
    fields = models.execute_kw(db, uid, password, 'account.move', 'fields_get', [], {'attributes': ['string', 'type', 'name']})
    
    print("\nCheck if move_line_ids exists on account.move:")
    if 'move_line_ids' in fields:
        print(f"YES: {fields['move_line_ids']}")
    else:
        print("NO: move_line_ids is NOT a field on account.move")

    # We can try to guess if sequence mixin is used by checking if 'sequence_prefix' exists (from SequenceMixin)
    if 'sequence_prefix' in fields:
        print("SequenceMixin seems to be active (sequence_prefix field found).")
    
    # We can't easily check _sequence_date_field value via RPC unless we have a method that exposes it.
    # But confirming the field existence is key.

if __name__ == "__main__":
    main()
