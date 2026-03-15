import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

ALL_COMPANIES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
MASTER_ID = 744

def add_companies_to_master():
    print(f"--- Adding All Companies to Master Account {MASTER_ID} ---")
    ctx = {'allowed_company_ids': ALL_COMPANIES}
    
    # Read current state
    master = models.execute_kw(db, uid, password, 'account.account', 'read', 
        [[MASTER_ID]], {'fields': ['name', 'code', 'company_ids'], 'context': ctx})
    print(f"Current: {master[0]}")
    
    # Add all companies using (4, id) command
    add_cmds = [(4, cid) for cid in ALL_COMPANIES]
    models.execute_kw(db, uid, password, 'account.account', 'write',
        [[MASTER_ID], {'company_ids': add_cmds}], {'context': ctx})
    
    # Verify
    master2 = models.execute_kw(db, uid, password, 'account.account', 'read', 
        [[MASTER_ID]], {'fields': ['name', 'code', 'company_ids'], 'context': ctx})
    print(f"After: {master2[0]}")

if __name__ == "__main__":
    add_companies_to_master()
