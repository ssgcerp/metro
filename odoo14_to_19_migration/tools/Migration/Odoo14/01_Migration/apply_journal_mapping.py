"""
Apply Journal Mapping to Queued Vendor Bill Migration Lines

Pre-processing step for migrate_vendor_bills_continuous.ps1.
Reads journal_mapping_o14.xlsx, queries Odoo 14 for each queued bill's journal,
and sets mapped_journal_id on the Odoo 19 migration line via XML-RPC.

Usage:
    python apply_journal_mapping.py --config ../06_odoo14_automigration/migration_config.json --mapping ../00_Logs_and_Reports/journal_mapping_o14.xlsx
"""

import argparse
import json
import logging
import os
import sys
import pandas as pd
import xmlrpc.client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class OdooClient:
    def __init__(self, config):
        self.url = config['url']
        self.db = config['db']
        self.username = config['username']
        self.password = config['password']
        self.uid = None
        self.models = None

    def authenticate(self):
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common', allow_none=True)
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            if self.uid:
                self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object', allow_none=True)
                return True
            return False
        except Exception as e:
            logger.error(f"Error authenticating to {self.url}: {e}")
            return False

    def execute(self, model, method, *args, **kwargs):
        if not self.uid:
            raise Exception("Not authenticated")
        return self.models.execute_kw(self.db, self.uid, self.password, model, method, args, kwargs)


def load_journal_mapping(excel_path):
    """Load journal mapping from Excel: Source Journal ID -> Dest Journal ID"""
    logger.info(f"Loading journal mapping from {excel_path}")
    try:
        df = pd.read_excel(excel_path)
        mapping = {}
        for _, row in df.iterrows():
            if pd.notna(row.get('Source Journal ID')) and pd.notna(row.get('Dest Journal ID')):
                mapping[int(row['Source Journal ID'])] = int(row['Dest Journal ID'])
        logger.info(f"Loaded {len(mapping)} journal mappings.")
        return mapping
    except Exception as e:
        logger.error(f"Failed to load journal mapping: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(description="Apply Journal Mapping to Queued Vendor Bills")
    parser.add_argument('--config', required=True, help='Path to migration_config.json')
    parser.add_argument('--mapping', required=True, help='Path to journal_mapping_o14.xlsx')
    args = parser.parse_args()

    # Resolve paths relative to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = args.config if os.path.isabs(args.config) else os.path.join(script_dir, args.config)
    mapping_path = args.mapping if os.path.isabs(args.mapping) else os.path.join(script_dir, args.mapping)

    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    if not os.path.exists(mapping_path):
        logger.error(f"Mapping file not found: {mapping_path}")
        sys.exit(1)

    with open(config_path, 'r') as f:
        config = json.load(f)

    # Load Excel mapping
    journal_mapping = load_journal_mapping(mapping_path)
    if not journal_mapping:
        logger.warning("No journal mappings loaded. Exiting (backend will use default Purchase journal fallback).")
        sys.exit(0)

    # Authenticate
    o14 = OdooClient(config['odoo14'])
    o19 = OdooClient(config['odoo19'])

    logger.info("Authenticating with Odoo 14...")
    if not o14.authenticate():
        logger.error("Failed to authenticate with Odoo 14")
        sys.exit(1)

    logger.info("Authenticating with Odoo 19...")
    if not o19.authenticate():
        logger.error("Failed to authenticate with Odoo 19")
        sys.exit(1)

    # Find queued migration lines WITHOUT mapped_journal_id
    queued_lines = o19.execute('vendor.bill.migration.line', 'search_read',
        [('status', '=', 'queued'), ('mapped_journal_id', '=', False)],
        fields=['id', 'uploaded_bill_number'],
    )

    if not queued_lines:
        logger.info("No queued bills without journal mapping found. Nothing to do.")
        sys.exit(0)

    logger.info(f"Found {len(queued_lines)} queued bill(s) without mapped_journal_id.")

    # Process each queued line
    mapped_count = 0
    skipped_count = 0
    not_found_count = 0

    for line in queued_lines:
        bill_number = line['uploaded_bill_number']
        line_id = line['id']

        # Look up the bill in Odoo 14 to get its journal_id
        try:
            o14_bills = o14.execute('account.move', 'search_read',
                [('name', '=', bill_number), ('move_type', '=', 'in_invoice')],
                fields=['journal_id'],
                limit=1,
            )
        except Exception as e:
            logger.warning(f"  Error fetching bill '{bill_number}' from Odoo 14: {e}")
            skipped_count += 1
            continue

        if not o14_bills:
            logger.warning(f"  Bill '{bill_number}' not found in Odoo 14")
            not_found_count += 1
            continue

        o14_journal_id = o14_bills[0].get('journal_id')
        if isinstance(o14_journal_id, (list, tuple)) and len(o14_journal_id) > 0:
            o14_journal_id_num = o14_journal_id[0]
            o14_journal_name = o14_journal_id[1] if len(o14_journal_id) > 1 else 'Unknown'
        else:
            logger.warning(f"  Bill '{bill_number}' has no journal_id in Odoo 14")
            skipped_count += 1
            continue

        # Look up mapping
        if o14_journal_id_num in journal_mapping:
            dest_journal_id = journal_mapping[o14_journal_id_num]
            try:
                o19.execute('vendor.bill.migration.line', 'write', [line_id], {
                    'mapped_journal_id': dest_journal_id
                })
                mapped_count += 1
                logger.info(f"  ✅ {bill_number}: Mapped journal '{o14_journal_name}' (O14 ID:{o14_journal_id_num}) -> O19 ID:{dest_journal_id}")
            except Exception as e:
                logger.error(f"  ❌ {bill_number}: Failed to write mapped_journal_id: {e}")
                skipped_count += 1
        else:
            logger.info(f"  ⚠️  {bill_number}: No mapping for journal '{o14_journal_name}' (O14 ID:{o14_journal_id_num}) — will use default Purchase journal")
            skipped_count += 1

    # Summary
    logger.info("")
    logger.info("=" * 50)
    logger.info("Journal Mapping Summary")
    logger.info("=" * 50)
    logger.info(f"  Total queued (unmapped): {len(queued_lines)}")
    logger.info(f"  Successfully mapped:     {mapped_count}")
    logger.info(f"  Skipped (no mapping):    {skipped_count}")
    logger.info(f"  Not found in Odoo 14:    {not_found_count}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
