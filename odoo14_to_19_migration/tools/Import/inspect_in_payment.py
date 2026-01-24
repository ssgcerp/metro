
import xmlrpc.client
import sys
import json

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print("INSPECTING 'IN PAYMENT' BILLS")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
    
    domain = [('move_type', '=', 'in_invoice'), ('payment_state', '=', 'in_payment')]
    bills = models.execute_kw(DB, uid, PASS, 'account.move', 'search_read', [domain], {'fields': ['id', 'name', 'amount_total', 'amount_residual', 'invoice_payments_widget'], 'limit': 10})
    
    print(f"Sample of {len(bills)} bills in 'in_payment':")
    for b in bills:
        print(f"\nBill: {b['name']} (ID {b['id']})")
        print(f"  Total: {b['amount_total']} | Residual: {b['amount_residual']}")
        widget = b.get('invoice_payments_widget')
        if widget:
            try:
                if isinstance(widget, str):
                    data = json.loads(widget)
                else:
                    data = widget
                content = data.get('content', [])
                print(f"  Linked Payments: {len(content)}")
                for item in content:
                    print(f"    - {item.get('title')} | Amount {item.get('amount')} | MoveID {item.get('move_id')}")
                    # Inspect the payment/move
                    mid = item.get('move_id')
                    if mid:
                        p_search = models.execute_kw(DB, uid, PASS, 'account.payment', 'search_read', [[('move_id', '=', mid)]], {'fields': ['id', 'name', 'state', 'outstanding_account_id']})
                        if p_search:
                            p = p_search[0]
                            print(f"      -> Payment {p['name']} ID {p['id']} State: {p['state']} | Outstanding: {p['outstanding_account_id']}")
                        
                        # Check move lines of this move
                        lines = models.execute_kw(DB, uid, PASS, 'account.move.line', 'search_read', [[('move_id', '=', mid), ('account_id.account_type', '!=', 'liability_payable')]], {'fields': ['account_id']})
                        for l in lines:
                             print(f"      -> Move Line ID {l['id']} Account: {l['account_id']}")
            except Exception as e:
                print(f"  Error reading widget: {e}")
        else:
            print("  No linked payments in widget.")

if __name__ == "__main__":
    main()
