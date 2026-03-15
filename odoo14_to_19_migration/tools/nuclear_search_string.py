import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def nuclear_search():
    string = "C3TMP"
    print(f"--- Nuclear Search for '{string}' in account.account ---")
    
    # Get all char fields
    comp_context = {'active_test': False}
    fields_info = models.execute_kw(db, uid, password, 'account.account', 'fields_get', [], {'attributes': ['type', 'string']})
    
    char_fields = [f for f, data in fields_info.items() 
                   if data['type'] in ('char', 'text') 
                   and data.get('store', True) 
                   and f not in ('activity_state', 'state', 'activity_type_icon')]
    print(f"Scanning {len(char_fields)} fields: {char_fields}")
    
    start_domain = []
    if len(char_fields) > 1:
        start_domain = ['|'] * (len(char_fields) - 1)
        
    domain_args = []
    for f in char_fields:
        domain_args.append((f, 'ilike', string))
        
    domain = start_domain + domain_args
    
    # But wait, execute_kw expects [domain_list]
    # And domain_list is [ '|', '|', (A), (B), (C) ]
    
    accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [domain],
        {'fields': ['id', 'name', 'code'], 'context': comp_context})
        
    print(f"Nuclear Matches: {len(accounts)}")
    for a in accounts:
        print(f"  MATCH: {a}")
        
    print("\n--- Checking Account Tax Groups ---")
    groups = models.execute_kw(db, uid, password, 'account.tax.group', 'search_read',
        [[('name', 'ilike', string)]],
        {'fields': ['id', 'name']})
    print(f"Tax Groups: {len(groups)}")
    for g in groups: print(f"  GROUP: {g}")

if __name__ == "__main__":
    nuclear_search()
