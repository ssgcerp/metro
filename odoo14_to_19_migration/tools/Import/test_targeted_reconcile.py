
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    bill_id = 53792 # SI-550100035722
    pay_id = 13344  # PPCSH/2025/00005
    
    print(f"TARGETED RECONCILE: Bill {bill_id} -> Payment {pay_id}")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
    
    # Get move lines
    b_lines = models.execute_kw(DB, uid, PASS, 'account.move.line', 'search', [[('move_id', '=', bill_id), ('account_type', '=', 'liability_payable')]])
    # Get payment move line
    p_rec = models.execute_kw(DB, uid, PASS, 'account.payment', 'read', [[pay_id], ['move_id']])[0]
    pmid = p_rec['move_id'][0]
    p_lines = models.execute_kw(DB, uid, PASS, 'account.move.line', 'search', [[('move_id', '=', pmid), ('account_type', '=', 'liability_payable')]])
    
    print(f"Bill Lines: {b_lines}")
    print(f"Payment Lines: {p_lines}")
    
    if b_lines and p_lines:
        all_lines = b_lines + p_lines
        print(f"Attempting reconcile of lines: {all_lines}")
        try:
            res = models.execute_kw(DB, uid, PASS, 'account.move.line', 'reconcile', [all_lines])
            print(f"Result: {res}")
        except Exception as e:
            print(f"Error: {e}")
            
if __name__ == "__main__":
    main()
