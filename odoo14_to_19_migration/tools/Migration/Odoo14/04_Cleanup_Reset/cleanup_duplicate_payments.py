
import pandas as pd
import argparse
import logging
import time
import requests
import random
import os
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
_logger = logging.getLogger(__name__)

# Odoo 19 Credentials (Target)
URL_19 = "https://metro.equdaierp.com"
DB_19 = "newdb"
USER_19 = "admin"
PASS_19 = "Amaze@321"

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
            response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers, timeout=300)
            res_json = response.json()
            if 'error' in res_json:
                _logger.error(f"RPC ERROR: {res_json['error']}")
            return res_json
        except Exception as e:
            _logger.error(f"RPC EXCEPTION: {e}")
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
             return None
        return result.get('result')

def main():
    if not os.path.exists('cleanup_data.json'):
        _logger.error("cleanup_data.json not found.")
        return
    
    with open('cleanup_data.json', 'r') as f:
        fix_data = json.load(f)
    
    to_delete_ids = [int(i) for i in fix_data.get('to_delete_ids', [])]
    if not to_delete_ids:
        _logger.info("No IDs to delete.")
        return

    _logger.info(f"Starting JSON-RPC cleanup of {len(to_delete_ids)} payments...")
    
    client = OdooJsonRpcClient(URL_19, DB_19, USER_19, PASS_19)
    if not client.authenticate():
        _logger.error("Authentication failed")
        return

    # 1. Fetch States
    batch_size = 100
    all_details = []
    for i in range(0, len(to_delete_ids), batch_size):
        batch = to_delete_ids[i:i+batch_size]
        details = client.execute_kw('account.payment', 'read', [batch, ['id', 'state', 'name']])
        if details:
            all_details.extend(details)
        _logger.info(f"  Fetched {len(all_details)}/{len(to_delete_ids)} states")

    draft_ids = [d['id'] for d in all_details if d['state'] == 'draft']
    paid_ids = [d['id'] for d in all_details if d['state'] == 'paid']
    in_process_ids = [d['id'] for d in all_details if d['state'] == 'in_process']
    cancel_ids = [d['id'] for d in all_details if d['state'] == 'canceled']

    _logger.info(f"Summary: {len(draft_ids)} draft, {len(paid_ids)} paid, {len(in_process_ids)} in_process, {len(cancel_ids)} canceled.")

    # A. Delete Draft/Canceled
    easy_to_delete = draft_ids + cancel_ids
    if easy_to_delete:
        _logger.info(f"Deleting {len(easy_to_delete)} draft/canceled...")
        for i in range(0, len(easy_to_delete), 50):
            batch = easy_to_delete[i:i+50]
            client.execute_kw('account.payment', 'unlink', [batch])
        _logger.info("  Deleted.")

    # B. Active Payments
    active_ids = paid_ids + in_process_ids
    if active_ids:
        _logger.info(f"Processing {len(active_ids)} active payments in batches...")
        batch_size = 20
        for i in range(0, len(active_ids), batch_size):
            batch = active_ids[i:i+batch_size]
            try:
                # 1. Try mass action_draft
                try: client.execute_kw('account.payment', 'action_draft', [batch])
                except: pass
                
                # 2. Try mass action_cancel
                try: client.execute_kw('account.payment', 'action_cancel', [batch])
                except: 
                    # Fallback to individual cancel if batch fails
                    for pid in batch:
                        try: client.execute_kw('account.payment', 'action_cancel', [[pid]])
                        except: pass
                
                # 3. Mass Unlink
                client.execute_kw('account.payment', 'unlink', [batch])
                _logger.info(f"  Deleted batch {i//batch_size + 1} ({len(batch)} records)")
                
            except Exception as e:
                _logger.error(f"  Batch {i} failed: {e}. Retrying individually...")
                for pid in batch:
                    try:
                        try: client.execute_kw('account.payment', 'action_draft', [[pid]])
                        except: pass
                        try: client.execute_kw('account.payment', 'action_cancel', [[pid]])
                        except: pass
                        client.execute_kw('account.payment', 'unlink', [[pid]])
                    except Exception as e2:
                        _logger.error(f"    Final failure for ID {pid}: {e2}")

    _logger.info("Cleanup successful.")

if __name__ == "__main__":
    main()
