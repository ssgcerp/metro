import xmlrpc.client

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, USER, PASS, {})
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

        for aid in [371, 414]:
            acc = models.execute_kw(DB, uid, PASS, 'account.account', 'read', [[aid], ['name', 'code', 'company_ids']])
            print(f"Account {aid}: {acc}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
