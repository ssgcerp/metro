
import argparse
import requests
import json
import random
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Odoo JSON-RPC Client
# -----------------------------------------------------------------------------
class OdooJsonRpcClient:
    def __init__(self, url, db, username, password):
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.uid = None

    def json_rpc(self, endpoint, params):
        data = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": params,
            "id": random.randint(0, 1000000000),
        }
        headers = {"Content-Type": "application/json"}
        try:
            response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers, timeout=60)
            return response.json()
        except Exception as e:
            logger.error(f"RPC Connection Failed: {e}")
            return None

    def authenticate(self):
        params = {"db": self.db, "login": self.username, "password": self.password}
        result = self.json_rpc("/web/session/authenticate", params)
        if result and 'result' in result and 'uid' in result['result']:
            self.uid = result['result']['uid']
            return True
        return False

    def execute_kw(self, model, method, args=None, kwargs=None):
        if args is None: args = []
        if kwargs is None: kwargs = {}
        params = {"model": model, "method": method, "args": args, "kwargs": kwargs}
        result = self.json_rpc("/web/dataset/call_kw", params)
        if result and 'error' in result:
             # Just verify if it is really an error or just None return
             # Usually error dict implies failure.
             logger.error(f"RPC Error ({method}): {result['error']}")
             return None
        return result.get('result')

# -----------------------------------------------------------------------------
# Fix Logic
# -----------------------------------------------------------------------------

def fix_taxes(url, db, user, password):
    logger.info("Connecting via JSON-RPC...")
    client = OdooJsonRpcClient(url, db, user, password)
    if not client.authenticate():
        logger.error("Authentication failed.")
        return

    # 1. Get Company Defaults
    logger.info("Caching Company Default Taxes...")
    companies = client.execute_kw('res.company', 'search_read', [[]], {'fields': ['name', 'account_purchase_tax_id']})
    
    comp_map = {} # CompID -> TaxID
    for c in companies:
        if c['account_purchase_tax_id']:
            comp_map[c['id']] = c['account_purchase_tax_id'][0] # (ID, Name)
        else:
            logger.warning(f"Company '{c['name']}' has NO Default Purchase Tax set.")
            
    # 2. Find Wrong Taxes
    logger.info("Finding '5% R C' Taxes...")
    wrong_taxes = client.execute_kw('account.tax', 'search_read', [[('name', 'ilike', '5% R C')]], {'fields': ['name', 'company_id']})
    
    if not wrong_taxes:
        logger.info("No taxes found matching '5% R C'. Exiting.")
        return
        
    for wt in wrong_taxes:
        wt_id = wt['id']
        wt_name = wt['name']
        comp_id = wt['company_id'][0]
        comp_name = wt['company_id'][1]
        
        target_tax = comp_map.get(comp_id)
        if not target_tax:
            logger.warning(f"Skipping Wrong Tax '{wt_name}' (ID {wt_id}) because Company '{comp_name}' has no default tax.")
            continue
            
        logger.info(f"Processing Wrong Tax: '{wt_name}' (ID {wt_id}) -> Target Tax ID {target_tax} (Comp: {comp_name})")
        
        # 3. Find Affected Lines and Group by Move
        domain = [
            ('move_id.move_type', '=', 'in_invoice'),
            ('tax_ids', 'in', [wt_id])
        ]
        
        lines = client.execute_kw('account.move.line', 'search_read', [domain], {'fields': ['move_id']})
        
        if not lines:
             logger.info("   No lines found.")
             continue
             
        # Extract unique move IDs
        move_ids = list(set([l['move_id'][0] for l in lines]))
        logger.info(f" - Found {len(lines)} lines across {len(move_ids)} bills.")
        
        # Process Bills
        count_processed = 0
        for m_id in move_ids:
            try:
                # 1. Check State
                move_data = client.execute_kw('account.move', 'read', [[m_id]], {'fields': ['state']})
                if not move_data: continue
                move = move_data[0]
                was_posted = (move['state'] == 'posted')
                
                # 2. Reset to Draft if needed
                if was_posted:
                    client.execute_kw('account.move', 'button_draft', [[m_id]])
                
                # 3. Update Lines
                line_domain = [('move_id', '=', m_id), ('tax_ids', 'in', [wt_id])]
                target_lines = client.execute_kw('account.move.line', 'search', [line_domain])
                
                if target_lines:
                    client.execute_kw('account.move.line', 'write', [target_lines, {'tax_ids': [(6, 0, [target_tax])]}])
                
                # 4. Post if needed
                if was_posted:
                    client.execute_kw('account.move', 'action_post', [[m_id]])
                
                count_processed += 1
                if count_processed % 10 == 0:
                    logger.info(f"   Processed {count_processed}/{len(move_ids)} bills...")
                    
            except Exception as e:
                logger.error(f"   Error processing bill {m_id}: {e}")
                
        logger.info(" - Completed tax update for this wrong tax.")

    logger.info("All Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://metro.equdaierp.com')
    parser.add_argument('--db', default='metrodb')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='Amaze@321')
    args = parser.parse_args()
    
    fix_taxes(args.url, args.db, args.user, args.password)
