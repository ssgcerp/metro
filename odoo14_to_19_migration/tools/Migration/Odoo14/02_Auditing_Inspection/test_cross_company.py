import requests
import json

def main():
    login_data = {'jsonrpc': '2.0', 'method': 'call', 'params': {'db': 'newdb', 'login': 'admin', 'password': 'Amaze@321'}, 'id': 1}
    r = requests.post('https://metro.equdaierp.com/web/session/authenticate', json=login_data)
    cookies = r.cookies
    
    # 1. Verify Invoice # 11601 company
    inv_data = {'jsonrpc': '2.0', 'method': 'call', 'params': {'model': 'account.move', 'method': 'search_read', 'args': [[('name', '=', '11601'), ('move_type', '=', 'out_invoice')]], 'kwargs': {'fields': ['id', 'name', 'company_id', 'partner_id']}}, 'id': 2}
    r = requests.post('https://metro.equdaierp.com/web/dataset/call_kw', cookies=cookies, json=inv_data)
    inv = r.json().get('result', [])
    if not inv:
        print("Invoice 11601 not found.")
        return
    print(f"Invoice: {inv[0]['name']} is in Company: {inv[0]['company_id']}")
    
    # 2. Try to create payment in Company 1 (Metro Fire)
    # Get a bank journal in Company 1
    j_data = {'jsonrpc': '2.0', 'method': 'call', 'params': {'model': 'account.journal', 'method': 'search', 'args': [[('company_id', '=', 1), ('type', '=', 'bank')]], 'kwargs': {'limit': 1}}, 'id': 3}
    r = requests.post('https://metro.equdaierp.com/web/dataset/call_kw', cookies=cookies, json=j_data)
    journal_id = r.json().get('result', [False])[0]
    
    if not journal_id:
        print("No bank journal found in Company 1.")
        return
    
    print(f"Attempting to create payment in Company 1 using journal {journal_id} for invoice in Company {inv[0]['company_id'][0]}...")
    
    pay_vals = {
        'payment_type': 'inbound',
        'partner_type': 'customer',
        'partner_id': inv[0]['partner_id'][0],
        'amount': 1.0,
        'date': '2025-01-01',
        'journal_id': journal_id,
        'company_id': 1,
        'memo': inv[0]['name'],
    }
    
    create_data = {'jsonrpc': '2.0', 'method': 'call', 'params': {'model': 'account.payment', 'method': 'create', 'args': [pay_vals], 'kwargs': {}}, 'id': 4}
    r = requests.post('https://metro.equdaierp.com/web/dataset/call_kw', cookies=cookies, json=create_data)
    res = r.json()
    
    if 'error' in res:
        print(f"CREATE FAILED: {res['error']}")
    else:
        pay_id = res['result']
        print(f"CREATE SUCCESS: Payment ID {pay_id}")
        
        # Try to post
        post_data = {'jsonrpc': '2.0', 'method': 'call', 'params': {'model': 'account.payment', 'method': 'action_post', 'args': [[pay_id]], 'kwargs': {}}, 'id': 5}
        r = requests.post('https://metro.equdaierp.com/web/dataset/call_kw', cookies=cookies, json=post_data)
        if 'error' in r.json():
            print(f"POST FAILED: {r.json()['error']}")
        else:
            print("POST SUCCESS")

if __name__ == "__main__":
    main()
