# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import base64
import io
import json
from datetime import datetime

try:
    from openpyxl import load_workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    import xlsxwriter
    XLSXWRITER_AVAILABLE = True
except ImportError:
    XLSXWRITER_AVAILABLE = False

_logger = logging.getLogger(__name__)


class CrmLeadUploadWizard(models.TransientModel):
    """Wizard for uploading Excel file with CRM lead data"""
    _name = 'crm.lead.upload.wizard'
    _description = 'CRM Lead Excel Upload Wizard'

    config_id = fields.Many2one(
        'odoo14.migration.config',
        string='Migration Configuration',
        required=False,
        help='Optional: Select Odoo 14 connection configuration for later status checking'
    )
    
    excel_file = fields.Binary(
        string='Excel File (.xlsx)',
        required=True,
        help='Upload Excel file with CRM lead data. Expected columns: Name, Customer, Contact Name, Email, Phone, Salesperson, Sales Team, Priority, Stage, Expected Revenue, Probability, Tags, Branch/ID, etc.'
    )
    
    excel_filename = fields.Char(string='Filename')
    
    leads_data_json = fields.Text(
        string='Parsed Leads Data (JSON)',
        help='Temporary storage for parsed Excel data'
    )

    error_report_file = fields.Binary(
        string='Error Report File',
        readonly=True,
        attachment=True,
        help='Excel file containing details of leads that failed to import.'
    )
    error_report_filename = fields.Char(string='Error Report Filename', readonly=True)

    def action_upload(self):
        """Process Excel upload and parse lead data"""
        self.ensure_one()
        
        if not OPENPYXL_AVAILABLE:
            raise UserError(
                'openpyxl library is required. Please install it:\n'
                'pip install openpyxl\n'
                'Then restart Odoo server.'
            )
        
        if not self.excel_file:
            raise UserError('Please select an Excel file to upload')
        
        try:
            # Decode file
            file_content = base64.b64decode(self.excel_file)
            workbook = load_workbook(io.BytesIO(file_content), data_only=True, read_only=True)
            sheet = workbook.active
            
            # Read header row to find column positions
            headers = []
            header_row = None
            for row_idx, row in enumerate(sheet.iter_rows(min_row=1, max_row=10, values_only=True), start=1):
                # Look for header row (first row with text in multiple cells)
                if row and any(cell and str(cell).strip() for cell in row[:10]):  # Check first 10 columns
                    # Check if this looks like a header (contains expected column names)
                    row_values = [str(cell).strip() if cell else '' for cell in row]
                    expected_headers = ['name', 'customer', 'contact name', 'email', 'phone', 'salesperson', 
                                      'sales team', 'priority', 'stage', 'expected revenue', 'probability', 
                                      'tags', 'branch/id', 'created on', 'opportunity', 'campaign', 'medium', 'source']
                    found_headers = sum(1 for val in row_values if val.lower() in [h.lower() for h in expected_headers])
                    
                    if found_headers >= 3:  # Found at least 3 expected headers
                        headers = row_values
                        header_row = row_idx
                        break
            
            if not headers or header_row is None:
                # Assume first row is header
                first_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
                if first_row:
                    headers = [str(cell).strip() if cell else '' for cell in first_row]
                    header_row = 1
                else:
                    raise UserError('Could not find header row in Excel file')
            
            # Find column indices (case-insensitive)
            col_map = {}
            header_lower = [h.lower() for h in headers]
            
            # Map all possible column names
            column_mappings = {
                'name': ['name'],
                'opportunity': ['opportunity'],
                'customer': ['customer'],
                'contact_name': ['contact name', 'contact'],
                'email': ['email'],
                'phone': ['phone'],
                'salesperson': ['salesperson', 'responsible user', 'user'],
                'sales_team': ['sales team', 'team'],
                'priority': ['priority'],
                'stage': ['stage'],
                'expected_revenue': ['expected revenue', 'revenue'],
                'probability': ['probability'],
                'tags': ['tags', 'tag'],
                'branch_id': ['branch/id', 'branch id', 'branch'],
                'created_on': ['created on', 'created', 'create date'],
                'campaign': ['campaign', 'campaign id'],
                'medium': ['medium'],
                'source': ['source'],
                'activities_deadline': ['my activities deadline', 'activities deadline', 'deadline'],
            }
            
            for key, possible_names in column_mappings.items():
                for name in possible_names:
                    if name in header_lower:
                        col_map[key] = header_lower.index(name)
                        break
            
            if 'name' not in col_map:
                raise UserError('Could not find "Name" column in Excel file. Please ensure the file has a "Name" column.')
            
            # Parse data rows
            leads_data = []
            for row_idx, row in enumerate(sheet.iter_rows(min_row=header_row + 1, values_only=True), start=header_row + 1):
                # Skip empty rows
                if not row or not any(cell for cell in row):
                    continue
                
                # Get name (required)
                name_col = col_map.get('name')
                if name_col is None or name_col >= len(row) or not row[name_col]:
                    continue
                
                lead_name = str(row[name_col]).strip()
                if not lead_name or lead_name.lower() in ['name', 'lead', 'opportunity', 'customer', 'draft']:  # Skip header values
                    continue
                
                # Build lead data
                lead_data = {
                    'name': lead_name,
                }
                
                # Get optional fields
                if 'opportunity' in col_map and col_map['opportunity'] < len(row):
                    opportunity_val = row[col_map['opportunity']]
                    if opportunity_val:
                        lead_data['is_opportunity'] = str(opportunity_val).strip().lower() in ['yes', 'true', '1', 'opportunity', 'y']
                
                if 'customer' in col_map and col_map['customer'] < len(row):
                    customer_val = row[col_map['customer']]
                    if customer_val:
                        lead_data['customer_name'] = str(customer_val).strip()
                
                if 'contact_name' in col_map and col_map['contact_name'] < len(row):
                    contact_name_val = row[col_map['contact_name']]
                    if contact_name_val:
                        lead_data['contact_name'] = str(contact_name_val).strip()
                
                if 'email' in col_map and col_map['email'] < len(row):
                    email_val = row[col_map['email']]
                    if email_val:
                        lead_data['email_from'] = str(email_val).strip()
                
                if 'phone' in col_map and col_map['phone'] < len(row):
                    phone_val = row[col_map['phone']]
                    if phone_val:
                        lead_data['phone'] = str(phone_val).strip()
                
                if 'salesperson' in col_map and col_map['salesperson'] < len(row):
                    salesperson_val = row[col_map['salesperson']]
                    if salesperson_val:
                        lead_data['salesperson_name'] = str(salesperson_val).strip()
                
                if 'sales_team' in col_map and col_map['sales_team'] < len(row):
                    team_val = row[col_map['sales_team']]
                    if team_val:
                        lead_data['team_name'] = str(team_val).strip()
                
                if 'priority' in col_map and col_map['priority'] < len(row):
                    priority_val = row[col_map['priority']]
                    if priority_val:
                        lead_data['priority'] = str(priority_val).strip()
                
                if 'stage' in col_map and col_map['stage'] < len(row):
                    stage_val = row[col_map['stage']]
                    if stage_val:
                        lead_data['stage_name'] = str(stage_val).strip()
                
                if 'expected_revenue' in col_map and col_map['expected_revenue'] < len(row):
                    revenue_val = row[col_map['expected_revenue']]
                    if revenue_val:
                        try:
                            if isinstance(revenue_val, str):
                                revenue_str = revenue_val.replace(',', '').replace('AED', '').replace('$', '').strip()
                                lead_data['expected_revenue'] = float(revenue_str)
                            else:
                                lead_data['expected_revenue'] = float(revenue_val)
                        except:
                            pass
                
                if 'probability' in col_map and col_map['probability'] < len(row):
                    probability_val = row[col_map['probability']]
                    if probability_val:
                        try:
                            lead_data['probability'] = float(probability_val)
                        except:
                            pass
                
                if 'tags' in col_map and col_map['tags'] < len(row):
                    tags_val = row[col_map['tags']]
                    if tags_val:
                        # Tags might be comma-separated
                        tags_str = str(tags_val).strip()
                        lead_data['tags'] = [t.strip() for t in tags_str.split(',') if t.strip()]
                
                if 'branch_id' in col_map and col_map['branch_id'] < len(row):
                    branch_id_val = row[col_map['branch_id']]
                    if branch_id_val:
                        try:
                            if isinstance(branch_id_val, str):
                                branch_id_str = branch_id_val.strip()
                                branch_id_str = ''.join(c for c in branch_id_str if c.isdigit() or c == '-')
                                if branch_id_str:
                                    lead_data['odoo14_branch_id'] = int(branch_id_str)
                            else:
                                lead_data['odoo14_branch_id'] = int(branch_id_val)
                        except (ValueError, TypeError):
                            pass
                
                if 'created_on' in col_map and col_map['created_on'] < len(row):
                    created_val = row[col_map['created_on']]
                    if created_val:
                        try:
                            if isinstance(created_val, str):
                                lead_data['create_date'] = created_val
                            else:
                                lead_data['create_date'] = str(created_val.date()) if hasattr(created_val, 'date') else str(created_val)
                        except:
                            pass
                
                if 'campaign' in col_map and col_map['campaign'] < len(row):
                    campaign_val = row[col_map['campaign']]
                    if campaign_val:
                        lead_data['campaign_name'] = str(campaign_val).strip()
                
                if 'medium' in col_map and col_map['medium'] < len(row):
                    medium_val = row[col_map['medium']]
                    if medium_val:
                        lead_data['medium_name'] = str(medium_val).strip()
                
                if 'source' in col_map and col_map['source'] < len(row):
                    source_val = row[col_map['source']]
                    if source_val:
                        lead_data['source_name'] = str(source_val).strip()
                
                if 'activities_deadline' in col_map and col_map['activities_deadline'] < len(row):
                    deadline_val = row[col_map['activities_deadline']]
                    if deadline_val:
                        try:
                            if isinstance(deadline_val, str):
                                lead_data['date_deadline'] = deadline_val
                            else:
                                lead_data['date_deadline'] = str(deadline_val.date()) if hasattr(deadline_val, 'date') else str(deadline_val)
                        except:
                            pass
                
                leads_data.append(lead_data)
            
            workbook.close()
            
            if not leads_data:
                raise UserError('No lead data found in Excel file. Please ensure the file contains lead records.')
            
            # Store parsed data for the Proceed button
            # Convert dates to strings for JSON serialization
            for lead_data in leads_data:
                for key in ['create_date', 'date_deadline']:
                    if key in lead_data and lead_data[key]:
                        if not isinstance(lead_data[key], str):
                            lead_data[key] = str(lead_data[key])
            
            self.leads_data_json = json.dumps(leads_data)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Excel Parsed Successfully',
                    'message': f'Found {len(leads_data)} lead(s). Click "Proceed" to import directly to CRM Leads.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except UserError:
            raise
        except Exception as e:
            _logger.error("Error uploading Excel: %s", str(e), exc_info=True)
            raise UserError('Error uploading Excel file: %s' % str(e))
    
    def action_proceed_import(self):
        """
        Import leads from parsed Excel data to both Migration Lines and CRM Leads.
        
        This method:
        1. Creates CRM Lead records in crm.lead model (visible in CRM Pipeline)
        2. Creates migration tracking records in crm.lead.migration.line model
        """
        self.ensure_one()
        
        if not self.leads_data_json:
            raise UserError('No parsed data found. Please upload Excel file first.')
        
        try:
            leads_data = json.loads(self.leads_data_json)
        except json.JSONDecodeError as e:
            _logger.error(f"JSON decode error: {str(e)}")
            raise UserError(f'Error parsing stored data: {str(e)}\n\nPlease upload Excel file again.')
        
        if not leads_data:
            raise UserError('No lead data found in parsed Excel file.')
        
        _logger.info(f"Starting import of {len(leads_data)} leads to both Migration Lines and CRM Leads")
        
        # Convert date strings back to date objects
        for lead_data in leads_data:
            for key in ['create_date', 'date_deadline']:
                if key in lead_data and lead_data[key]:
                    try:
                        if isinstance(lead_data[key], str):
                            # Try to parse date - handle various formats
                            try:
                                from dateutil import parser
                                parsed_date = parser.parse(lead_data[key])
                                lead_data[key] = parsed_date.date()
                            except ImportError:
                                # If dateutil not available, try simple format
                                from datetime import datetime
                                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
                                    try:
                                        parsed_date = datetime.strptime(lead_data[key].split()[0], fmt)
                                        lead_data[key] = parsed_date.date()
                                        break
                                    except:
                                        continue
                                else:
                                    lead_data[key] = None
                    except:
                        lead_data[key] = None
        
        LeadModel = self.env['crm.lead']
        MigrationLineModel = self.env['crm.lead.migration.line']
        created_count = 0
        skipped_count = 0
        errors = []
        error_details_list = []  # List of dicts with 'lead' and 'customer' keys for Excel report
        created_lead_ids = []
        created_migration_line_ids = []
        
        # Check which leads already exist
        lead_names = [l.get('name') for l in leads_data if l.get('name')]
        if not lead_names:
            raise UserError('No valid lead names found in Excel data.')
        
        existing_leads = LeadModel.search([('name', 'in', lead_names)])
        existing_names = set(existing_leads.mapped('name'))
        
        existing_migration_lines = MigrationLineModel.search([('uploaded_lead_name', 'in', lead_names)])
        existing_migration_names = set(existing_migration_lines.mapped('uploaded_lead_name'))
        
        _logger.info(f"Found {len(existing_names)} existing leads and {len(existing_migration_names)} existing migration lines out of {len(lead_names)} total")
        
        processed_count = 0
        for idx, lead_data in enumerate(leads_data, 1):
            lead_name = lead_data.get('name')
            if not lead_name:
                _logger.warning(f"Row {idx}: Missing lead name, skipping")
                continue
            
            # Skip header values
            if lead_name.lower() in ['name', 'lead', 'opportunity', 'customer', 'draft']:
                _logger.info(f"Row {idx}: Skipping potential header row with name '{lead_name}'")
                continue

            processed_count += 1
            
            # Prepare data for migration line (always create/update this)
            customer_name = lead_data.get('customer_name')
            lead_exists = lead_name in existing_names
            
            # Try to create/update lead if it doesn't exist
            lead = None
            lead_error = None
            
            # Use savepoint to handle transaction errors
            savepoint_name = f'crm_lead_import_{idx}'
            savepoint_created = False
            try:
                # Check if transaction is already aborted
                try:
                    self.env.cr.execute('SELECT 1')
                except Exception:
                    _logger.error(f"Transaction aborted before processing lead {lead_name}, rolling back all changes")
                    self.env.cr.rollback()
                    raise UserError("Database transaction was aborted. Please try the import again.")

                self.env.cr.execute(f'SAVEPOINT {savepoint_name}')
                savepoint_created = True
                
                if lead_exists:
                    # Lead already exists - skip it and continue to next
                    lead = None
                    for existing_lead in existing_leads:
                        if existing_lead.name == lead_name:
                            lead = existing_lead
                            break
                    if not lead:
                        lead = LeadModel.search([('name', '=', lead_name)], limit=1)
                    skipped_count += 1
                    _logger.info(f"Lead '{lead_name}' already exists in CRM Leads - SKIPPING and continuing with next record")
                    
                    # Still create/update migration line for tracking
                    try:
                        existing_line = MigrationLineModel.search([
                            ('uploaded_lead_name', '=', lead_name)
                        ], limit=1)
                        
                        if existing_line:
                            # Update existing migration line
                            existing_line.write({
                                'status': 'already_migrated',
                                'status_message': f'Already exists in CRM Leads (ID: {lead.id if lead else "N/A"})',
                                'odoo19_lead_id': lead.id if lead else False,
                            })
                        else:
                            # Create new migration line
                            MigrationLineModel.create({
                                'uploaded_lead_name': lead_name,
                                'config_id': self.config_id.id if self.config_id else False,
                                'status': 'already_migrated',
                                'status_message': f'Already exists in CRM Leads (ID: {lead.id if lead else "N/A"})',
                                'odoo19_lead_id': lead.id if lead else False,
                                'migration_date': fields.Datetime.now(),
                            })
                    except Exception as e:
                        _logger.warning(f"Could not create/update migration line for existing lead {lead_name}: {str(e)}")
                    
                    # Release savepoint and continue to next record
                    if savepoint_created:
                        try:
                            self.env.cr.execute(f'RELEASE SAVEPOINT {savepoint_name}')
                        except Exception as release_error:
                            _logger.warning(f"Error releasing savepoint: {release_error}")
                    continue  # Skip to next lead
                else:
                    # Try to create the lead
                    try:
                        # Find customer/partner by name
                        partner = False
                        if customer_name:
                            partner = self.env['res.partner'].search([
                                ('name', '=', customer_name)
                            ], limit=1)
                            
                            if not partner:
                                partner = self.env['res.partner'].search([
                                    ('name', 'ilike', customer_name)
                                ], limit=1)
                            
                            if not partner:
                                lead_error = f'Customer "{customer_name}" not found'
                                _logger.warning(f"Customer not found: {customer_name} for lead {lead_name}")
                        
                        # Find user/salesperson by name
                        user = False
                        salesperson_name = lead_data.get('salesperson_name')
                        if salesperson_name and not lead_error:
                            user = self.env['res.users'].search([
                                ('name', 'ilike', salesperson_name)
                            ], limit=1)
                            if not user:
                                # Try login
                                user = self.env['res.users'].search([
                                    ('login', '=', salesperson_name)
                                ], limit=1)
                        
                        # Find team by name
                        team = False
                        team_name = lead_data.get('team_name')
                        if team_name and not lead_error:
                            team = self.env['crm.team'].search([
                                ('name', 'ilike', team_name)
                            ], limit=1)
                        
                        # Find stage by name
                        stage = False
                        stage_name = lead_data.get('stage_name')
                        if stage_name and not lead_error:
                            stage = self.env['crm.stage'].search([
                                ('name', '=', stage_name)
                            ], limit=1)
                            if not stage:
                                stage = self.env['crm.stage'].search([
                                    ('name', 'ilike', stage_name)
                                ], limit=1)
                        
                        # Find company from branch mapping if branch_id is provided
                        company = False
                        odoo14_branch_id = lead_data.get('odoo14_branch_id')
                        if odoo14_branch_id and not lead_error:
                            mapping_model = self.env['odoo14.branch.company.mapping']
                            company = mapping_model.get_company_for_branch(odoo14_branch_id)
                            if not company:
                                # Use default company if mapping not found
                                company = self.env.company
                        elif not lead_error:
                            company = self.env.company
                        
                        # Handle tags
                        tag_ids = []
                        tags_list = lead_data.get('tags', [])
                        if tags_list and not lead_error:
                            for tag_name in tags_list:
                                tag = self.env['crm.tag'].search([
                                    ('name', '=', tag_name)
                                ], limit=1)
                                if not tag:
                                    # Create tag if it doesn't exist
                                    tag = self.env['crm.tag'].create({'name': tag_name})
                                tag_ids.append(tag.id)
                        
                        if not lead_error:
                            # Determine type (lead or opportunity)
                            type_val = 'opportunity' if lead_data.get('is_opportunity') else 'lead'
                            
                            # Handle priority (0, 1, 2, 3 or '0', '1', '2', '3')
                            priority_val = '1'  # default
                            priority_input = lead_data.get('priority', '')
                            if priority_input:
                                priority_str = str(priority_input).strip()
                                if priority_str.lower() in ['0', '1', '2', '3']:
                                    priority_val = priority_str
                                elif priority_str.lower() in ['normal']:
                                    priority_val = '1'
                                elif priority_str.lower() in ['high', 'important']:
                                    priority_val = '2'
                                elif priority_str.lower() in ['very high', 'urgent']:
                                    priority_val = '3'
                                elif priority_str.lower() in ['low']:
                                    priority_val = '0'
                            
                            # Prepare lead values
                            lead_vals = {
                                'name': lead_name,
                                'partner_id': partner.id if partner else False,
                                'contact_name': lead_data.get('contact_name', False),
                                'email_from': lead_data.get('email_from', False),
                                'phone': lead_data.get('phone', False),
                                'user_id': user.id if user else False,
                                'team_id': team.id if team else False,
                                'stage_id': stage.id if stage else False,
                                'priority': priority_val,
                                'type': type_val,
                                'expected_revenue': lead_data.get('expected_revenue', 0.0),
                                'probability': lead_data.get('probability', 0) if lead_data.get('probability') else False,
                                'date_deadline': lead_data.get('date_deadline', False),
                                'company_id': company.id if company else self.env.company.id,
                            }
                            
                            if tag_ids:
                                lead_vals['tag_ids'] = [(6, 0, tag_ids)]
                            
                            # Create CRM Lead in crm.lead model (CRM module)
                            # This creates the lead in the CRM Pipeline/Kanban view
                            # Use sudo() to bypass multi-company access restrictions
                            # This is acceptable for migration scenarios where we need to create records
                            # across different companies
                            lead = LeadModel.sudo().create(lead_vals)
                            created_lead_ids.append(lead.id)
                            created_count += 1
                            _logger.info(f"Created CRM lead '{lead_name}' (ID: {lead.id}) in crm.lead model - visible in CRM Pipeline")
                            
                            # Preserve creation date if provided
                            create_date = lead_data.get('create_date')
                            if create_date:
                                try:
                                    self.env.cr.execute(
                                        """
                                        UPDATE crm_lead
                                           SET create_date = %s,
                                               write_date = COALESCE(write_date, %s)
                                         WHERE id = %s
                                        """,
                                        (create_date, create_date, lead.id),
                                    )
                                except Exception as e:
                                    _logger.warning(f"Could not set original create_date: {str(e)}")
                    
                    except Exception as e:
                        lead_error = str(e)
                        _logger.error(f"Error creating lead {lead_name}: {lead_error}", exc_info=True)
                        try:
                            self.env.cr.execute(f'ROLLBACK TO SAVEPOINT {savepoint_name}')
                        except Exception as rollback_error:
                            _logger.error(f"Error rolling back to savepoint: {rollback_error}")
                
                # Always create/update Migration Line
                try:
                    existing_line = MigrationLineModel.search([
                        ('uploaded_lead_name', '=', lead_name)
                    ], limit=1)
                    
                    if existing_line:
                        # Update existing migration line
                        update_vals = {}
                        if lead:
                            update_vals.update({
                                'status': 'migrated',
                                'status_message': 'Imported directly from Excel via Upload Wizard',
                                'odoo19_lead_id': lead.id,
                                'migration_date': fields.Datetime.now(),
                            })
                        elif lead_error:
                            update_vals.update({
                                'status': 'error',
                                'status_message': f'Lead creation failed: {lead_error}',
                                'error_message': lead_error,
                            })
                        existing_line.write(update_vals)
                        _logger.info(f"Updated migration line for lead {lead_name}")
                    else:
                        # Create new migration line
                        migration_line_vals = {
                            'uploaded_lead_name': lead_name,
                            'config_id': self.config_id.id if self.config_id else False,
                        }
                        if lead:
                            migration_line_vals.update({
                                'status': 'migrated',
                                'status_message': 'Imported directly from Excel via Upload Wizard',
                                'odoo19_lead_id': lead.id,
                                'migration_date': fields.Datetime.now(),
                            })
                        elif lead_error:
                            migration_line_vals.update({
                                'status': 'error',
                                'status_message': f'Lead creation failed: {lead_error}',
                                'error_message': lead_error,
                            })
                        else:
                            migration_line_vals.update({
                                'status': 'pending_migration',
                                'status_message': 'Awaiting lead creation',
                            })
                        migration_line = MigrationLineModel.create(migration_line_vals)
                        created_migration_line_ids.append(migration_line.id)
                        _logger.info(f"Created migration line for lead {lead_name}")
                
                except Exception as e:
                    _logger.error(f"Error creating/updating migration line for {lead_name}: {str(e)}", exc_info=True)
                    if lead_error:
                        errors.append(f'Lead {lead_name}: {lead_error} (Migration line also failed: {str(e)})')
                    else:
                        errors.append(f'Lead {lead_name}: Migration line failed: {str(e)}')
                    if savepoint_created:
                        try:
                            self.env.cr.execute(f'ROLLBACK TO SAVEPOINT {savepoint_name}')
                        except Exception as rollback_error:
                            _logger.error(f"Error rolling back to savepoint: {rollback_error}")
                    continue

                # Release savepoint if successful
                if savepoint_created:
                    try:
                        self.env.cr.execute(f'RELEASE SAVEPOINT {savepoint_name}')
                    except Exception as release_error:
                        _logger.error(f"Error releasing savepoint: {release_error}")
                        self.env.cr.rollback()
                        raise UserError(f'Transaction error releasing savepoint for lead {lead_name}: {release_error}. Please try again.')
                
            except Exception as e:
                _logger.error(f"Error in savepoint block for {lead_name}: {str(e)}", exc_info=True)
                if savepoint_created:
                    try:
                        self.env.cr.execute(f'ROLLBACK TO SAVEPOINT {savepoint_name}')
                    except Exception as rollback_error:
                        _logger.error(f"Error rolling back to savepoint in outer handler: {rollback_error}")
                        self.env.cr.rollback()
                        raise UserError(f'Transaction corrupted after error with lead {lead_name}. All changes rolled back. Please try again.')
                errors.append(f'Lead {lead_name}: {str(e)}')
                continue
            
            # Track errors for report
            if lead_error and not lead_exists:
                errors.append(f'Lead {lead_name}: {lead_error}')
                error_details_list.append({
                    'lead': lead_name,
                    'customer': customer_name,
                    'error': lead_error
                })
            
            # Commit more frequently to avoid transaction issues
            if idx % 50 == 0:
                try:
                    self.env.cr.commit()
                    _logger.info(f"Progress: Created {created_count}/{len(leads_data)} leads and {len(created_migration_line_ids)} migration lines (committed at row {idx})")
                except Exception as commit_error:
                    _logger.error(f"Error committing at row {idx}: {commit_error}")
                    self.env.cr.rollback()
                    raise UserError(f'Error committing batch at row {idx}: {commit_error}. Processed {created_count} leads so far.')
        
        self.env.cr.commit()
        _logger.info(f"Import completed: {processed_count} processed, {created_count} leads created, {len(created_migration_line_ids)} migration lines created, {skipped_count} skipped, {len(errors)} errors")
        
        if processed_count == 0:
            raise UserError('No leads were processed. Please check that the Excel file contains valid lead names.')
        
        # Generate error report if there are errors
        error_report_filename = False
        if error_details_list and XLSXWRITER_AVAILABLE:
            try:
                output = io.BytesIO()
                workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                worksheet = workbook.add_worksheet('Failed Leads')
                
                bold = workbook.add_format({'bold': True})
                
                headers = ['Lead Name', 'Customer', 'Error Message']
                for col_num, header in enumerate(headers):
                    worksheet.write(0, col_num, header, bold)
                
                for row_num, error_detail in enumerate(error_details_list, start=1):
                    worksheet.write(row_num, 0, error_detail.get('lead', ''))
                    worksheet.write(row_num, 1, error_detail.get('customer', ''))
                    worksheet.write(row_num, 2, error_detail.get('error', ''))
                
                for i, _ in enumerate(headers):
                    worksheet.set_column(i, i, 20)
                
                workbook.close()
                output.seek(0)
                
                error_report_filename = f'crm_lead_import_errors_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                self.write({
                    'error_report_file': base64.b64encode(output.read()),
                    'error_report_filename': error_report_filename,
                })
                _logger.info(f"Generated error report: {error_report_filename}")
            except Exception as e:
                _logger.error(f"Error generating Excel error report: {str(e)}", exc_info=True)
                errors.append(f"Error generating Excel error report: {str(e)}")
        elif error_details_list and not XLSXWRITER_AVAILABLE:
            _logger.warning("xlsxwriter library not available, cannot generate Excel error report.")
            errors.append("xlsxwriter library not available, cannot generate Excel error report.")

        if errors:
            _logger.warning(f"Import errors summary: {len(errors)} errors occurred")
            for error in errors[:10]:
                _logger.warning(f"  - {error}")
        
        # Prepare summary message
        if created_count > 0:
            notification_title = 'Import Successful'
            notification_msg = f'Successfully created {created_count} lead(s) in CRM Leads'
            if len(created_migration_line_ids) > 0:
                notification_msg += f' and {len(created_migration_line_ids)} migration line(s) in CRM Lead Migration'
            if skipped_count > 0:
                notification_msg += f'\nSkipped {skipped_count} lead(s) (already exist)'
            if errors:
                notification_msg += f'\n{len(errors)} error(s) occurred'
            notification_type = 'success' if not errors else 'warning'
        else:
            notification_title = 'Import Failed'
            notification_msg = f'No leads were created. '
            if skipped_count > 0:
                notification_msg += f'{skipped_count} already exist. '
            if errors:
                notification_msg += f'{len(errors)} error(s) occurred.'
                error_preview = '\n'.join(errors[:5])
                if len(errors) > 5:
                    error_preview += f'\n... and {len(errors) - 5} more (check server logs)'
                notification_msg += f'\n\nErrors:\n{error_preview}'
            else:
                notification_msg += 'Please check the data.'
            notification_type = 'danger'
        
        # Return action to view leads or show errors with download option
        # Leads are created in crm.lead model (CRM module) - they will appear in CRM Pipeline
        if created_count > 0:
            action = {
                'type': 'ir.actions.act_window',
                'name': f'CRM Leads - {created_count} Imported',
                'res_model': 'crm.lead',
                'view_mode': 'kanban,list,form',
                'domain': [('id', 'in', created_lead_ids)],
                'target': 'current',
                'context': {'search_default_my_leads': 0},  # Show all leads, not just "My Leads"
            }
            if error_details_list and error_report_filename:
                action['context'] = {
                    'error_report_available': True,
                    'error_report_filename': error_report_filename,
                }
            return action
        else:
            if errors:
                error_preview = '\n'.join(errors[:10])
                if len(errors) > 10:
                    error_preview += f'\n... and {len(errors) - 10} more errors'
                full_message = f'{notification_msg}\n\nError Details:\n{error_preview}'
                
                if error_report_filename:
                    full_message += f'\n\nError report Excel file has been generated and is available for download.'
            else:
                full_message = notification_msg
            
            if error_report_filename:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Import Completed - Errors Found',
                    'res_model': 'crm.lead.upload.wizard',
                    'view_mode': 'form',
                    'res_id': self.id,
                    'target': 'new',
                    'context': {'error_report_available': True},
                }
            else:
                raise UserError(f'{notification_title}\n\n{full_message}')

    def action_download_error_report(self):
        """Download the error report Excel file"""
        self.ensure_one()
        if not self.error_report_file:
            raise UserError('No error report available.')
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/error_report_file/{self.error_report_filename}?download=true',
            'target': 'self',
        }
