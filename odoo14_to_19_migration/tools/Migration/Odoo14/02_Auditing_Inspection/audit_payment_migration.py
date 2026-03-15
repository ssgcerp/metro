
import xmlrpc.client
import logging
import ssl
import pandas as pd
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Odoo 14 Credentials (Source)
URL_14 = "https://erpmfs.com"
DB_14 = "metro_production_8_8_22"
USER_14 = "Sales.auh@metrofiresystems.com"
PASS_14 = "Sales@185734"

# Odoo 19 Credentials (Target)
URL_19 = "https://metro.equdaierp.com"
DB_19 = "newdb" 
USER_19 = "admin"
PASS_19 = "Amaze@321"

def get_connection(url, db, user, password):
    try:
        ctx = ssl._create_unverified_context()
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ctx)
        uid = common.authenticate(db, user, password, {})
        if not uid:
            return None, None
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ctx)
        return uid, models
    except Exception as e:
        logger.error(f"Connection failed for {url}: {e}")
        return None, None

def audit():
    global DB_19
    logger.info("Connecting to Odoo 14...")
    uid_14, models_14 = get_connection(URL_14, DB_14, USER_14, PASS_14)
    if not uid_14:
        logger.error("Failed to connect to Odoo 14")
        return

    logger.info("Connecting to Odoo 19...")
    uid_19, models_19 = get_connection(URL_19, DB_19, USER_19, PASS_19)
    if not uid_19:
        logger.error(f"Failed to connect to Odoo 19 with DB '{DB_19}'")
        return
    
    logger.info(f"Connected. Using Odoo 19 DB: {DB_19}")

    # 1. Fetch Odoo 14 Payments
    logger.info("Fetching Odoo 14 payments...")
    domain_14 = [
        ('payment_type', '=', 'inbound'),
        ('partner_type', '=', 'customer'),
        ('state', '=', 'posted')
    ]
    payments_14 = models_14.execute_kw(DB_14, uid_14, PASS_14, 'account.payment', 'search_read', [domain_14], 
                                     {'fields': ['name', 'amount', 'date', 'partner_id', 'branch_id', 'ref']})
    
    df14 = pd.DataFrame(payments_14)
    df14['partner_id_name'] = df14['partner_id'].apply(lambda x: x[1] if x else False)
    logger.info(f"Odoo 14: Found {len(df14)} posted inbound customer payments.")

    # 2. Fetch Odoo 19 Payments
    logger.info("Fetching Odoo 19 payments...")
    domain_19 = [
        ('payment_type', '=', 'inbound'),
        ('partner_type', '=', 'customer'),
    ]
    payments_19 = models_19.execute_kw(DB_19, uid_19, PASS_19, 'account.payment', 'search_read', [domain_19], 
                                     {'fields': ['name', 'amount', 'date', 'partner_id', 'company_id', 'state', 'memo']})
    
    df19 = pd.DataFrame(payments_19)
    df19['partner_id_name'] = df19['partner_id'].apply(lambda x: x[1] if x else False)
    logger.info(f"Odoo 19: Found {len(df19)} inbound customer payments.")

    # 3. Matching Logic
    # Strict matching: O14 name/ref must be in O19 name or memo.
    
    report_data = []
    found_in_o19_ids = set()
    
    logger.info("Analyzing matches (Strict)...")
    for _, row14 in df14.iterrows():
        o14_name = row14['name']
        o14_ref = row14['ref'] or ''
        o14_amount = row14['amount']
        o14_date = row14['date']
        o14_partner = row14['partner_id_name']
        
        # Strict Match in O19
        # memo usually contains the O14 name or ref
        matches = df19[
            (df19['name'] == o14_name) | 
            (df19['memo'] == o14_name) | 
            (df19['memo'] == o14_ref)
        ]
        
        if len(matches) == 0:
            # Check for weak match just for reporting, but don't mark as Match if it's too risky
            weak_matches = df19[
                ((df19['amount'] == o14_amount) & (df19['date'] == o14_date) & (df19['partner_id_name'] == o14_partner))
            ]
            if len(weak_matches) > 0:
                for _, match in weak_matches.iterrows():
                    # We report it as 'Potential' but not 'Matched' for strict cleanup
                    report_data.append({
                        'Source': 'O14',
                        'Name/ID': o14_name,
                        'Ref/Memo': o14_ref,
                        'Amount': o14_amount,
                        'Date': o14_date,
                        'Partner': o14_partner,
                        'Status': 'Potential Match',
                        'O19 ID': match['id'],
                        'O19 Name': match['name'],
                        'O19 Memo': match['memo'],
                        'O19 State': match['state']
                    })
            
            report_data.append({
                'Source': 'O14',
                'Name/ID': o14_name,
                'Ref/Memo': o14_ref,
                'Amount': o14_amount,
                'Date': o14_date,
                'Partner': o14_partner,
                'Status': 'Missing',
                'Details': 'No strict match found in O19'
            })
        else:
            for _, match in matches.iterrows():
                found_in_o19_ids.add(match['id'])
                report_data.append({
                    'Source': 'O14',
                    'Name/ID': o14_name,
                    'Ref/Memo': o14_ref,
                    'Amount': o14_amount,
                    'Date': o14_date,
                    'Partner': o14_partner,
                    'Status': 'Matched',
                    'O19 ID': match['id'],
                    'O19 Name': match['name'],
                    'O19 Memo': match['memo'],
                    'O19 State': match['state']
                })

    # 4. Find Unmatched O19 records (Potential extra duplicates or independent entries)
    unmatched_o19 = df19[~df19['id'].isin(found_in_o19_ids)]
    for _, row19 in unmatched_o19.iterrows():
        report_data.append({
            'Source': 'O19',
            'Name/ID': row19['name'],
            'Ref/Memo': row19['memo'],
            'Amount': row19['amount'],
            'Date': row19['date'],
            'Partner': row19['partner_id_name'],
            'Status': 'Extra',
            'Details': 'Record in O19 not linked to any O14 payment'
        })

    # 5. Export Report
    if report_data:
        report_file = f"payment_audit_refined_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        pd.DataFrame(report_data).to_excel(report_file, index=False)
        logger.info(f"Refined audit report saved to {report_file}")
    else:
        logger.info("No data to report.")

if __name__ == "__main__":
    audit()
