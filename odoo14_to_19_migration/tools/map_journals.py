import xmlrpc.client
import logging
import pandas as pd

# Odoo 19 Credentials (Source)
URL_SRC = "https://metro.equdaierp.com"
DB_SRC = "metrodb"
USER_SRC = "admin"
PASS_SRC = "Amaze@321"

# Odoo 19 Credentials (Target)
URL_TGT = "https://metro.equdaierp.com"
DB_TGT = "newdb"
USER_TGT = "admin"
PASS_TGT = "Amaze@321"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def map_journals():
    try:
        # Connect to Source
        common_src = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_SRC))
        uid_src = common_src.authenticate(DB_SRC, USER_SRC, PASS_SRC, {})
        models_src = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_SRC))
        logger.info(f"Connected to Source DB: {DB_SRC}")

        # Connect to Target
        common_tgt = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_TGT))
        uid_tgt = common_tgt.authenticate(DB_TGT, USER_TGT, PASS_TGT, {})
        models_tgt = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_TGT))
        logger.info(f"Connected to Target DB: {DB_TGT}")

        # Fetch Journals from Source (Bank and Cash usually for payments)
        domain = [('type', 'in', ['bank', 'cash'])]
        journals_src = models_src.execute_kw(DB_SRC, uid_src, PASS_SRC, 'account.journal', 'search_read',
            [domain], {'fields': ['id', 'name', 'code', 'type', 'company_id']})

        # Fetch Journals from Target
        journals_tgt = models_tgt.execute_kw(DB_TGT, uid_tgt, PASS_TGT, 'account.journal', 'search_read',
            [domain], {'fields': ['id', 'name', 'code', 'type', 'company_id']})

        # Create a mapping dictionary for target journals by name
        tgt_journal_map = {j['name']: j for j in journals_tgt}

        mapping_results = []
        for j_src in journals_src:
            src_name = j_src['name']
            src_code = j_src['code']
            j_type = j_src['type']
            src_company = j_src.get('company_id')
            src_comp_name = src_company[1] if src_company else 'N/A'
            
            tgt_match = tgt_journal_map.get(src_name)
            if tgt_match:
                status = "Mapped by exact name"
                tgt_name = tgt_match['name']
                tgt_code = tgt_match['code']
                tgt_company = tgt_match.get('company_id')
                tgt_comp_name = tgt_company[1] if tgt_company else 'N/A'
            else:
                status = "Not Found in Target - PLEASE MAP MANUALLY"
                tgt_name = ""
                tgt_code = ""
                tgt_comp_name = ""

            mapping_results.append({
                'Source Name (metrodb)': src_name,
                'Source Code': src_code,
                'Source Company': src_comp_name,
                'Type': j_type,
                'Target Name (newdb)': tgt_name,
                'Target Code': tgt_code,
                'Target Company': tgt_comp_name,
                'Mapping Status': status
            })

        # Print mapping table
        df = pd.DataFrame(mapping_results)
        print("\n--- Journal Mapping (Odoo 19 metrodb -> Odoo 19 newdb) ---")
        print(df.to_string(index=False))
        
        # Save to excel as well
        df.to_excel("journal_mapping_metrodb_to_newdb.xlsx", index=False)
        print("\nMapping saved to journal_mapping_metrodb_to_newdb.xlsx")

    except Exception as e:
        logger.error(f"Error mapping journals: {e}")

if __name__ == "__main__":
    map_journals()
