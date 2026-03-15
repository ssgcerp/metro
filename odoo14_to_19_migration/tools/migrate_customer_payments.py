import xmlrpc.client
import logging
import argparse
import sys
import os
import pandas as pd
from datetime import datetime

# Odoo 19 Credentials (Target)
URL_19 = "https://metro.equdaierp.com"
DB_19 = "newdb"
USER_19 = "admin"
PASS_19 = "Amaze@321"

# Odoo 19 Credentials (Source - metrodb)
URL_SRC = "https://metro.equdaierp.com"
DB_SRC = "metrodb"
USER_SRC = "admin"
PASS_SRC = "Amaze@321"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def load_journal_mapping():
    mapping_file = r'e:\odoo modules\19\metro\odoo14_to_19_migration\tools\journal_mapping_metrodb_to_newdb.xlsx'
    try:
        df = pd.read_excel(mapping_file)
        # Create a dictionary of (Source Name, Source Company) -> Target Name
        mapping = {}
        for _, row in df.iterrows():
            src_name = row['Source Name (metrodb)']
            src_comp = row['Source Company']
            tgt_name = row['Target Name (newdb)']
            if pd.notna(tgt_name) and str(tgt_name).strip() != "":
                mapping[(src_name, src_comp)] = str(tgt_name).strip()
        logger.info(f"Loaded {len(mapping)} journal mappings from Excel.")
        return mapping
    except Exception as e:
        logger.error(f"Failed to load journal mapping: {e}")
        return {}

def migrate_payments(dry_run=True, limit=10):
    report_data = []
    journal_mapping = load_journal_mapping()
    if not journal_mapping:
        logger.error("No valid journal mappings found, cannot proceed.")
        return

    try:
        # Connect to Odoo 19 (Target - newdb)
        common_tgt = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_19), allow_none=True)
        uid_tgt = common_tgt.authenticate(DB_19, USER_19, PASS_19, {})
        if uid_tgt:
            logger.info("Connected to Target Odoo 19 (newdb).")
        else:
            logger.error("Failed to authenticate with Target Odoo 19.")
            return

        models_tgt = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_19), allow_none=True)
        
        # Connect to Odoo 19 (Source - metrodb)
        common_src = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_SRC), allow_none=True)
        uid_src = common_src.authenticate(DB_SRC, USER_SRC, PASS_SRC, {})
        if uid_src:
            logger.info(f"Connected to Source Odoo 19 ({DB_SRC}).")
        else:
            logger.error("Failed to authenticate with Source Odoo 19.")
            return

        models_src = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_SRC), allow_none=True)

        logger.info(f"Fetching Customer Payments from {DB_SRC} (Limit: {limit})...")
        
        # Fetch inbound customer payments
        domain_src = [('payment_type', '=', 'inbound'), ('partner_type', '=', 'customer'), ('state', 'in', ['in_process', 'paid', 'posted'])]
        payments_src = models_src.execute_kw(DB_SRC, uid_src, PASS_SRC, 'account.payment', 'search_read', 
            [domain_src], 
            {'fields': ['name', 'amount', 'currency_id', 'date', 'state', 'journal_id', 'payment_method_line_id', 'reconciled_invoice_ids', 'partner_id', 'company_id'], 
             'limit': limit,
             'order': 'id asc'})

        if not payments_src:
            logger.info(f"No payments found in {DB_SRC} to migrate.")
            return
            
        logger.info(f"Found {len(payments_src)} payments to process.")

        migrated_count = 0
        failed_count = 0

        for p_src in payments_src:
            pay_name_src = p_src['name']
            pay_amount = p_src['amount']
            pay_date = p_src['date']
            journal_src = p_src['journal_id']
            partner_src = p_src['partner_id']
            company_src = p_src.get('company_id')
            reconciled_inv_ids = p_src.get('reconciled_invoice_ids', [])
            
            src_j_name = journal_src[1] if journal_src else ''
            src_c_name = company_src[1] if company_src else 'N/A'
            
            if 'Mysore' not in src_c_name:
                continue
            
            
            report_row = {
                'Source_Payment_Name': pay_name_src,
                'Amount': pay_amount,
                'Source_Customer': partner_src[1] if partner_src else '',
                'Source_Journal': src_j_name,
                'Source_Company': src_c_name,
                'Linked_Invoices_Source': '',
                'Target_Payment_ID': '',
                'Target_Customer': '',
                'Target_Journal': '',
                'Status': 'Failed',
                'Error_Reason': ''
            }

            try:
                # 1. Fetch related invoice names from Source
                inv_names = []
                if reconciled_inv_ids:
                    invs_src = models_src.execute_kw(DB_SRC, uid_src, PASS_SRC, 'account.move', 'read', 
                        [reconciled_inv_ids], {'fields': ['name']})
                    inv_names = [inv['name'] for inv in invs_src]
                    report_row['Linked_Invoices_Source'] = ", ".join(inv_names)
                else:
                    report_row['Linked_Invoices_Source'] = "None"
                    
                # 2. Check if payment already exists in Target by name
                existing_tgt = models_tgt.execute_kw(DB_19, uid_tgt, PASS_19, 'account.payment', 'search', 
                    [[('name', '=', pay_name_src)]], {'limit': 1})
                if existing_tgt:
                    report_row['Status'] = 'Skipped'
                    report_row['Error_Reason'] = f"Payment {pay_name_src} already exists in Target"
                    logger.info(f"Payment {pay_name_src} already exists. Skipped.")
                    report_data.append(report_row)
                    continue

                # 3. Match Journal in Target via Excel Mapping
                journal_id_tgt = None
                if journal_src:
                    tgt_j_name = journal_mapping.get((src_j_name, src_c_name))
                    if tgt_j_name:
                        # Find exactly this journal in Target
                        j_domain = [('name', '=', tgt_j_name), ('type', 'in', ['bank', 'cash'])]
                        j_tgt = models_tgt.execute_kw(DB_19, uid_tgt, PASS_19, 'account.journal', 'search_read', 
                            [j_domain], {'fields': ['id', 'name', 'default_account_id'], 'limit': 1})
                        if j_tgt:
                            journal_id_tgt = j_tgt[0]['id']
                            report_row['Target_Journal'] = j_tgt[0]['name']
                        else:
                            raise ValueError(f"Mapped Target Journal '{tgt_j_name}' not found in Target DB")
                    else:
                        raise ValueError(f"No mapping provided in excel for Source Journal: '{src_j_name}' (Company: {src_c_name})")
                else:
                    raise ValueError("No journal found on Source payment")

                # 4. Determine Partner from Invoices (Preferred) or Partner matched by name
                partner_id_tgt = None
                matched_invs_tgt = []
                if inv_names:
                    # Search for the invoices in Target
                    for inv_name in inv_names:
                        inv_tgt = models_tgt.execute_kw(DB_19, uid_tgt, PASS_19, 'account.move', 'search_read', 
                            [[('name', '=', inv_name), ('move_type', '=', 'out_invoice')]], 
                            {'fields': ['id', 'partner_id', 'state'], 'limit': 1})
                        
                        if inv_tgt:
                            matched_invs_tgt.append(inv_tgt[0])
                            if partner_id_tgt is None and inv_tgt[0].get('partner_id'):
                                partner_id_tgt = inv_tgt[0]['partner_id'][0]
                                report_row['Target_Customer'] = inv_tgt[0]['partner_id'][1]
                        else:
                            logger.warning(f"Could not find invoice {inv_name} in Target DB for payment {pay_name_src}")
                
                # Fallback to mapping partner by name
                if partner_id_tgt is None and partner_src:
                    p_name = partner_src[1]
                    partner_tgt = models_tgt.execute_kw(DB_19, uid_tgt, PASS_19, 'res.partner', 'search', 
                        [[('name', '=', p_name)]], {'limit': 1})
                    if partner_tgt:
                        partner_id_tgt = partner_tgt[0]
                        report_row['Target_Customer'] = p_name
                    else:
                        raise ValueError(f"Customer '{p_name}' not found in Target DB")

                if not partner_id_tgt:
                    raise ValueError("Could not determine customer for payment")

                # 5. Fetch Payment Method Line ID for Inbound Manual
                pml_method = models_tgt.execute_kw(DB_19, uid_tgt, PASS_19, 'account.payment.method.line', 'search_read', 
                    [[('payment_type', '=', 'inbound'), ('journal_id', '=', journal_id_tgt), ('code', '=', 'manual')]], 
                    {'fields': ['id'], 'limit': 1})
                
                if pml_method:
                    pml_id_tgt = pml_method[0]['id']
                else:
                    # fallback to any inbound method for this journal
                    pml_method = models_tgt.execute_kw(DB_19, uid_tgt, PASS_19, 'account.payment.method.line', 'search_read', 
                        [[('payment_type', '=', 'inbound'), ('journal_id', '=', journal_id_tgt)]], 
                        {'fields': ['id'], 'limit': 1})
                    if pml_method:
                        pml_id_tgt = pml_method[0]['id']
                    else:
                        raise ValueError(f"No inbound payment method line found for mapped journal {tgt_j_name} in Target DB")

                # 6. Create the Payment Draft
                payment_vals = {
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': partner_id_tgt,
                    'amount': pay_amount,
                    'date': pay_date,
                    'journal_id': journal_id_tgt,
                    'payment_method_line_id': pml_id_tgt,
                    'payment_reference': f"Migrated from {pay_name_src}",
                }
                
                # Remove None values to avoid xmlrpc marshalling errors
                payment_vals = {k: v for k, v in payment_vals.items() if v is not None}
                
                if not dry_run:
                    # Debug dictionary
                    try:
                        new_pay_id = models_tgt.execute_kw(DB_19, uid_tgt, PASS_19, 'account.payment', 'create', [payment_vals])
                        report_row['Target_Payment_ID'] = new_pay_id
                    except Exception as e:
                        logger.error(f"Error creating payment {pay_name_src} with vals: {payment_vals}")
                        raise e
                    
                    # 7. Post the Payment
                    try:
                        models_tgt.execute_kw(DB_19, uid_tgt, PASS_19, 'account.payment', 'action_post', [[new_pay_id]])
                    except Exception as err:
                        if "cannot marshal None unless allow_none is enabled" in str(err):
                            logger.info(f"Payment {new_pay_id} posted (ignored None return)")
                        else:
                            raise err
                    
                    # 8. Force write standard bank account to avoid "In Payment" status (make it "paid")
                    if j_tgt[0].get('default_account_id'):
                        bank_acc_id = j_tgt[0]['default_account_id'][0]
                        try:
                            models_tgt.execute_kw(DB_19, uid_tgt, PASS_19, 'account.payment', 'write', [[new_pay_id], {'outstanding_account_id': bank_acc_id}])
                        except Exception as err:
                            if "cannot marshal None unless allow_none is enabled" in str(err):
                                logger.info(f"Payment {new_pay_id} outstanding_account updated (ignored None return)")
                            else:
                                raise err

                    # 9. Reconcile with matched invoices
                    if matched_invs_tgt:
                        # Get the payment move lines (receivable account)
                        pay_data = models_tgt.execute_kw(DB_19, uid_tgt, PASS_19, 'account.payment', 'read', [[new_pay_id], ['move_id']])[0]
                        pay_move_id = pay_data['move_id'][0]
                        
                        p_lines = models_tgt.execute_kw(DB_19, uid_tgt, PASS_19, 'account.move.line', 'search', [
                            [('move_id', '=', pay_move_id), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]
                        ])
                        
                        if p_lines:
                            for inv in matched_invs_tgt:
                                inv_name = inv['name'] if isinstance(inv, dict) and 'name' in inv else "Unknown"
                                if inv['state'] != 'posted':
                                    continue # Cannot reconcile unposted invoice
                                b_lines = models_tgt.execute_kw(DB_19, uid_tgt, PASS_19, 'account.move.line', 'search', [
                                    [('move_id', '=', inv['id']), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]
                                ])
                                
                                if b_lines:
                                    try:
                                        # Ensure we're passing a flat list of integer IDs
                                        line_ids = [line for line in (p_lines + b_lines) if line is not None]
                                        try:
                                            models_tgt.execute_kw(DB_19, uid_tgt, PASS_19, 'account.move.line', 'reconcile', [line_ids])
                                            logger.info(f"Reconciled payment {new_pay_id} with invoice {inv_name}")
                                        except Exception as err:
                                            # Odoo 19 reconcile might return None, which causes xmlrpc TypeError. Ignore it.
                                            if "cannot marshal None unless allow_none is enabled" in str(err):
                                                logger.info(f"Reconciled payment {new_pay_id} with invoice {inv_name} (ignored None return)")
                                            else:
                                                logger.error(f"Reconcile payload failed: {line_ids}")
                                                raise err
                                    except Exception as e:
                                        logger.error(f"Failed to reconcile payment {new_pay_id} with invoice {inv_name}: {e}")
                                        report_row['Error_Reason'] += f"Recon Error: {e} | "

                    report_row['Status'] = 'Success'
                    migrated_count += 1
                else:
                    report_row['Status'] = 'Dry Run Success'
                    migrated_count += 1
                    
            except Exception as e:
                report_row['Status'] = 'Failed'
                report_row['Error_Reason'] = str(e)
                failed_count += 1
                logger.error(f"Failed to process payment {pay_name_src}: {e}")

            report_data.append(report_row)

        # Output Excel Report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = "dryrun_" if dry_run else "live_"
        excel_filename = f"{prefix}metrodb_to_newdb_payments_migration_{timestamp}.xlsx"
        
        df = pd.DataFrame(report_data)
        df.to_excel(excel_filename, index=False)
        logger.info(f"Report saved to {excel_filename}")
        
        logger.info(f"Migration Complete | Processed: {len(report_data)} | Success: {migrated_count} | Failed/Skipped: {failed_count}")

    except Exception as e:
        logger.error(f"Global Error: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate Customer Payments from Odoo 19 (metrodb) to Odoo 19 (newdb)")
    parser.add_argument('--run', action='store_true', help="Execute changes in newdb (disables dry-run)")
    parser.add_argument('--limit', type=int, default=10, help="Number of records to process")
    
    args = parser.parse_args()
    
    migrate_payments(dry_run=not args.run, limit=args.limit)
