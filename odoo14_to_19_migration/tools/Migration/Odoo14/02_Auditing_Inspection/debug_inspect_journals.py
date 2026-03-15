import requests
import json

def main():
    login_data = {'jsonrpc': '2.0', 'method': 'call', 'params': {'db': 'newdb', 'login': 'admin', 'password': 'Amaze@321'}, 'id': 1}
    r = requests.post('https://metro.equdaierp.com/web/session/authenticate', json=login_data)
    cookies = r.cookies
    
    comp_data = {'jsonrpc': '2.0', 'method': 'call', 'params': {'model': 'res.company', 'method': 'search_read', 'args': [[('name', 'in', ['FUJAIRAH', 'ABU DHABI', 'DUBAI', 'AJMAN', 'RAS AL KHAIMAH', 'SHARJAH'])]], 'kwargs': {'fields': ['id', 'name']}}, 'id': 2}
    r = requests.post('https://metro.equdaierp.com/web/dataset/call_kw', cookies=cookies, json=comp_data)
    companies = r.json().get('result', [])
    print(f"Companies: {companies}")
    
    for c in companies:
        name = c['name']
        cid = c['id']
        j_data = {'jsonrpc': '2.0', 'method': 'call', 'params': {'model': 'account.journal', 'method': 'search_read', 'args': [[('company_id', '=', cid)]], 'kwargs': {'fields': ['id', 'name', 'type']}}, 'id': 3}
        rj = requests.post('https://metro.equdaierp.com/web/dataset/call_kw', cookies=cookies, json=j_data)
        journals = rj.json().get('result', [])
        print(f"Journals for {name} ({cid}):")
        for j in journals:
            print(f"  - {j['name']} (ID: {j['id']}, Type: {j['type']})")

if __name__ == "__main__":
    main()
