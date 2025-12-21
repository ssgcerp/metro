# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import json
import ast
import base64

_logger = logging.getLogger(__name__)


class CustomerMigrationWizard(models.TransientModel):
    _name = 'odoo14.customer.migration.wizard'
    _description = 'Customer Migration Wizard'

    config_id = fields.Many2one(
        'odoo14.migration.config',
        string='Migration Configuration',
        required=True,
        help='Select the Odoo 14 connection configuration'
    )
    
    # Customer migration items - Fixed fields for each model
    customers_count = fields.Integer(string='Customers Total Count', default=0, readonly=True)
    customers_migrated = fields.Integer(string='Customers Migrated', default=0, readonly=True)
    
    quotations_count = fields.Integer(string='Quotations Total Count', default=0, readonly=True)
    quotations_migrated = fields.Integer(string='Quotations Migrated', default=0, readonly=True)
    quotations_progress = fields.Float(string='Quotations Progress %', compute='_compute_quotations_progress', store=False)
    quotations_offset = fields.Integer(string='Quotations Offset', default=0, readonly=True, help='Current offset position for batch processing')
    start_quotation_number = fields.Integer(
        string='Start From Quotation #',
        default=1,
        help='1‑based index of the Odoo 14 quotation to start from. '
             'For example, set 31 to start after the first 30 records.'
    )
    
    sales_orders_count = fields.Integer(string='Sales Orders Total Count', default=0, readonly=True)
    sales_orders_migrated = fields.Integer(string='Sales Orders Migrated', default=0, readonly=True)
    
    invoices_count = fields.Integer(string='Invoices Total Count', default=0, readonly=True)
    invoices_migrated = fields.Integer(string='Invoices Migrated', default=0, readonly=True)

    # Migration state and status
    is_migrating = fields.Boolean(string='Migration in Progress', default=False, readonly=True)
    migration_status = fields.Text(string='Migration Status', readonly=True)

    # Logs for exporting skipped and error records
    quotation_skipped_log = fields.Text(string='Skipped Quotations (CSV)', readonly=True)
    quotation_error_log = fields.Text(string='Quotation Errors (CSV)', readonly=True)
    
    # Legacy field for backward compatibility
    customer_items = fields.One2many(
        'odoo14.customer.migration.item',
        'wizard_id',
        string='Customer Items'
    )

    @api.depends('quotations_count', 'quotations_migrated')
    def _compute_quotations_progress(self):
        for record in self:
            if record.quotations_count:
                record.quotations_progress = (record.quotations_migrated / record.quotations_count) * 100
            else:
                record.quotations_progress = 0.0
    
    def action_check_customers(self):
        """Check customers count"""
        # For Odoo 14, use customer field (boolean)
        # Try multiple approaches: customer=True OR has sale orders
        return self._check_model('customers', 'res.partner', "[('customer', '=', True)]")
    
    def action_check_quotations(self):
        """Check quotations count - all quotations regardless of state"""
        return self._check_model('quotations', 'sale.order', "[]")
    
    def action_check_sales_orders(self):
        """Check sales orders count"""
        return self._check_model('sales_orders', 'sale.order', "[('state', '=', 'sale')]")
    
    def action_check_invoices(self):
        """Check invoices count"""
        return self._check_model('invoices', 'account.invoice', "[('type', '=', 'out_invoice')]")
    
    def _check_model(self, model_type, model_name, domain_str):
        """Check count for a specific model"""
        self.ensure_one()
        if not self.config_id:
            raise UserError('Please select a migration configuration first.')
        
        try:
            from ..models.odoo14_api_client import Odoo14APIClient
            import json
            
            client = Odoo14APIClient(
                url=self.config_id.odoo14_url,
                db=self.config_id.odoo14_database,
                username=self.config_id.odoo14_username,
                password=self.config_id.odoo14_password
            )
            
            if not client.authenticate():
                raise UserError('Failed to authenticate with Odoo 14. Please test the connection first.')
            
            # Use XML-RPC to get count (more reliable than REST API)
            # Parse domain string (it's Python syntax, not JSON)
            if domain_str:
                try:
                    domain = ast.literal_eval(domain_str)
                except:
                    # Fallback to JSON if ast fails
                    try:
                        domain = json.loads(domain_str)
                    except:
                        domain = []
            else:
                domain = []
            
            # For res.partner, first get total partners count
            total_partners = 0
            if model_name == 'res.partner':
                try:
                    total_partners = client.count(model_name, [])
                    _logger.info("Total partners (no domain): %s" % total_partners)
                except Exception as e:
                    _logger.error("Error getting total partners: %s" % str(e))
                    raise UserError('Failed to connect to Odoo 14. Error: %s' % str(e))
            
            # Handle customer field differences between Odoo 14 and 15+
            # Odoo 14 uses 'customer' field (boolean), Odoo 15+ uses 'customer_rank' (integer)
            # But some Odoo 14 instances might not have the 'customer' field
            customer_field_exists = None
            if model_name == 'res.partner' and domain:
                # Check if customer field exists by trying to use it
                customer_field_exists = False
                try:
                    # Try a test search with customer field
                    test_result = client.count(model_name, [('customer', '=', True)])
                    customer_field_exists = True
                    _logger.info("Customer field exists, test count: %s" % test_result)
                except Exception as e:
                    error_str = str(e)
                    if "Invalid field" in error_str or "customer" in error_str.lower():
                        customer_field_exists = False
                        _logger.warning("Customer field does not exist in this Odoo 14 instance")
                        # Use empty domain - we'll use total partners count
                        domain = []
                    else:
                        _logger.error("Error testing customer field: %s" % error_str)
                        raise
                
                if customer_field_exists:
                    # Convert customer_rank domain to customer domain for Odoo 14
                    new_domain = []
                    for d in domain:
                        if d[0] == 'customer_rank' and len(d) == 3:
                            # Convert customer_rank > 0 to customer = True
                            if d[1] in ('>', '>=', '!=') and d[2] > 0:
                                new_domain.append(('customer', '=', True))
                            elif d[1] == '=' and d[2] == 0:
                                new_domain.append(('customer', '=', False))
                            else:
                                new_domain.append(d)
                        elif d[0] == 'customer' and len(d) == 3:
                            # Keep customer domain as is
                            new_domain.append(d)
                        else:
                            new_domain.append(d)
                    domain = new_domain
                
                # Log the domain for debugging
                _logger.info("Using domain for res.partner: %s (customer_field_exists: %s)" % (domain, customer_field_exists))
            
            # Handle account.invoice vs account.move
            if model_name == 'account.invoice':
                invoice_model = client._get_invoice_model()
                if invoice_model:
                    model_name = invoice_model
                    if invoice_model == 'account.move':
                        domain = [d if d[0] != 'type' else ('move_type', d[1], d[2]) for d in domain]
            
            # Get count via XML-RPC
            _logger.info("Getting count for model: %s, domain: %s" % (model_name, domain))
            
            try:
                # If domain is empty for res.partner, it means customer field doesn't exist
                # Use total partners as count
                if model_name == 'res.partner' and not domain:
                    _logger.info("Customer field doesn't exist, using total partners (%s) as customer count" % total_partners)
                    count = total_partners
                else:
                    count = client.count(model_name, domain)
                    _logger.info("XML-RPC count for %s with domain %s: %s" % (model_name, domain, count))
                    
                    # If count is 0 and we have total partners, use total partners
                    if model_name == 'res.partner' and count == 0 and total_partners > 0:
                        _logger.warning("Customer count is 0 but total partners is %s. Using total partners." % total_partners)
                        count = total_partners
                
                # If count is 0 and we're checking customers, try alternative approaches
                if count == 0 and model_name == 'res.partner' and total_partners > 0:
                    _logger.info("Count is 0 but total partners is %s, checking if customer field exists..." % total_partners)
                    
                    # Check if customer field exists by trying to read a partner
                    try:
                        # Get first partner to check fields
                        test_partners = client.search_read(model_name, [], ['name'], limit=1)
                        if test_partners:
                            # Try to read customer field
                            try:
                                test_with_customer = client.search_read(model_name, [], ['customer'], limit=1)
                                _logger.info("Customer field exists in this instance")
                            except:
                                _logger.info("Customer field does NOT exist in this instance")
                                # Use total partners as customer count
                                count = total_partners
                                _logger.info("Using total partners (%s) as customer count" % count)
                    except Exception as e:
                        _logger.error("Error checking partner fields: %s" % str(e))
                        # If we can't check, use total partners as fallback
                        if total_partners > 0:
                            count = total_partners
                            _logger.info("Using total partners (%s) as customer count (fallback)" % count)
                
            except Exception as e:
                error_str = str(e)
                _logger.error("Error getting count via XML-RPC for %s: %s" % (model_name, error_str))
                
                # If error is about invalid customer field and we have total partners, use that
                if model_name == 'res.partner' and ("Invalid field" in error_str or "customer" in error_str.lower()):
                    if total_partners > 0:
                        _logger.info("Customer field error detected, using total partners (%s) as count" % total_partners)
                        count = total_partners
                    else:
                        # Try without domain as fallback
                        try:
                            _logger.info("Trying without domain...")
                            count = client.count(model_name, [])
                            _logger.info("XML-RPC count for %s without domain: %s" % (model_name, count))
                        except Exception as e2:
                            _logger.error("Error even without domain: %s" % str(e2))
                            raise UserError('Failed to get count for %s: %s' % (model_name, str(e)))
                else:
                    # Try without domain as fallback
                    try:
                        _logger.info("Trying without domain...")
                        count = client.count(model_name, [])
                        _logger.info("XML-RPC count for %s without domain: %s" % (model_name, count))
                    except Exception as e2:
                        _logger.error("Error even without domain: %s" % str(e2))
                        raise UserError('Failed to get count for %s: %s' % (model_name, str(e)))
            
            # Update the appropriate field
            field_map = {
                'customers': ('customers_count', 'customers_migrated'),
                'quotations': ('quotations_count', 'quotations_migrated'),
                'sales_orders': ('sales_orders_count', 'sales_orders_migrated'),
                'invoices': ('invoices_count', 'invoices_migrated'),
            }
            
            count_field, _ = field_map.get(model_type, (None, None))
            if count_field:
                self.write({count_field: count})
            
            # Return action to reload the form so buttons become visible when count > 0
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'views': [(False, 'form')],
            }
        except Exception as e:
            _logger.error("Error checking %s: %s" % (model_type, str(e)))
            raise UserError('Error checking %s: %s' % (model_type, str(e)))
    
    def action_preview_customers(self):
        """Preview customers"""
        self.ensure_one()
        if self.customers_count == 0:
            raise UserError('No customers found. Please check data first.')
        
        if not self.config_id:
            raise UserError('Please select a migration configuration first.')
        
        try:
            from ..models.odoo14_api_client import Odoo14APIClient
            
            client = Odoo14APIClient(
                url=self.config_id.odoo14_url,
                db=self.config_id.odoo14_database,
                username=self.config_id.odoo14_username,
                password=self.config_id.odoo14_password
            )
            
            if not client.authenticate():
                raise UserError('Failed to authenticate with Odoo 14. Please test the connection first.')
            
            # Get first customer
            domain = []
            customers = client.search_read('res.partner', domain, 
                ['name', 'email', 'phone', 'mobile', 'street', 'city', 'country_id'], 
                limit=1, offset=0)
            
            if not customers:
                raise UserError('No customers found to preview.')
            
            # Create preview record
            preview = self.env['odoo14.customer.preview'].create({
                'wizard_id': self.id,
                'config_id': self.config_id.id,
                'current_index': 0,
                'total_count': self.customers_count,
            })
            
            # Load first customer
            preview._load_customer(offset=0)
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'odoo14.customer.preview',
                'res_id': preview.id,
                'view_mode': 'form',
                'target': 'new',
                'name': 'Customer Preview (%s of %s)' % (1, self.customers_count),
            }
        except UserError:
            raise
        except Exception as e:
            _logger.error("Error previewing customers: %s" % str(e))
            raise UserError('Error previewing customers: %s' % str(e))
    
    def action_preview_quotations(self):
        """Preview quotations"""
        self.ensure_one()
        if self.quotations_count == 0:
            raise UserError('No quotations found. Please check data first.')
        
        if not self.config_id:
            raise UserError('Please select a migration configuration first.')
        
        try:
            from ..models.odoo14_api_client import Odoo14APIClient
            
            client = Odoo14APIClient(
                url=self.config_id.odoo14_url,
                db=self.config_id.odoo14_database,
                username=self.config_id.odoo14_username,
                password=self.config_id.odoo14_password
            )
            
            if not client.authenticate():
                raise UserError('Failed to authenticate with Odoo 14. Please test the connection first.')
            
            # Create preview record
            preview = self.env['odoo14.quotation.preview'].create({
                'wizard_id': self.id,
                'config_id': self.config_id.id,
                'current_index': 0,
                'total_count': self.quotations_count,
            })
            
            # Load first quotation
            preview._load_quotation(offset=0)
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'odoo14.quotation.preview',
                'res_id': preview.id,
                'view_mode': 'form',
                'target': 'new',
                'name': 'Quotation Preview (%s of %s)' % (1, self.quotations_count),
            }
        except UserError:
            raise
        except Exception as e:
            _logger.error("Error previewing quotations: %s" % str(e))
            raise UserError('Error previewing quotations: %s' % str(e))
    
    def action_preview_sales_orders(self):
        """Preview sales orders"""
        if self.sales_orders_count == 0:
            raise UserError('No sales orders found. Please check data first.')
        # TODO: Implement preview
        return {'type': 'ir.actions.act_window_close'}
    
    def action_preview_invoices(self):
        """Preview invoices"""
        if self.invoices_count == 0:
            raise UserError('No invoices found. Please check data first.')
        # TODO: Implement preview
        return {'type': 'ir.actions.act_window_close'}
    
    def action_migrate_customers(self):
        """Migrate customers from Odoo 14 to Odoo 19"""
        self.ensure_one()
        if self.customers_count == 0:
            raise UserError('No customers found. Please check data first.')
        
        if not self.config_id:
            raise UserError('Please select a migration configuration first.')
        
        try:
            from ..models.odoo14_api_client import Odoo14APIClient
            
            client = Odoo14APIClient(
                url=self.config_id.odoo14_url,
                db=self.config_id.odoo14_database,
                username=self.config_id.odoo14_username,
                password=self.config_id.odoo14_password
            )
            
            if not client.authenticate():
                raise UserError('Failed to authenticate with Odoo 14. Please test the connection first.')
            
            # Get all customers from Odoo 14
            domain = []
            customers = client.search_read('res.partner', domain, 
                ['name', 'email', 'phone', 'mobile', 'street', 'street2', 'city', 
                 'state_id', 'zip', 'country_id', 'vat', 'is_company'], 
                limit=self.customers_count, offset=0)
            
            if not customers:
                raise UserError('No customers found to migrate.')
            
            migrated = 0
            skipped = 0
            errors = 0
            
            # Migrate customers in batches
            batch_size = 50
            for i in range(0, len(customers), batch_size):
                batch = customers[i:i+batch_size]
                
                for customer_data in batch:
                    try:
                        # Check for duplicates
                        name = customer_data.get('name', '').strip()
                        email = customer_data.get('email', '').strip() if customer_data.get('email') else ''
                        vat = customer_data.get('vat', '').strip() if customer_data.get('vat') else ''
                        
                        # Search for existing customer by name first (most reliable)
                        existing = False
                        if name:
                            existing = self.env['res.partner'].search([
                                ('name', '=', name)
                            ], limit=1)
                        
                        # If not found by name, check by email or VAT
                        if not existing:
                            search_domain = []
                            if email:
                                search_domain.append(('email', '=', email))
                            if vat:
                                search_domain.append(('vat', '=', vat))
                            
                            if search_domain:
                                if len(search_domain) == 2:
                                    # Both email and VAT - use OR
                                    search_domain = ['|'] + search_domain
                                existing = self.env['res.partner'].search(search_domain, limit=1)
                        
                        if existing:
                            skipped += 1
                            _logger.info("Skipping duplicate customer: %s (found existing: %s)" % (name, existing.name))
                            continue
                        
                        # Create customer
                        partner_vals = self._prepare_customer_vals(customer_data)
                        self.env['res.partner'].create(partner_vals)
                        migrated += 1
                        
                        # Update progress every 10 records
                        if migrated % 10 == 0:
                            self.write({'customers_migrated': migrated})
                            self.env.cr.commit()
                            _logger.info("Progress: Migrated %s/%s customers" % (migrated, len(customers)))
                    
                    except Exception as e:
                        errors += 1
                        _logger.error("Error migrating customer %s: %s" % (customer_data.get('name', 'Unknown'), str(e)))
                        continue
                
                # Update progress after each batch
                self.write({'customers_migrated': migrated})
                self.env.cr.commit()
            
            # Final update
            self.write({'customers_migrated': migrated})
            self.env.cr.commit()
            
            message = 'Migration complete! Migrated: %s, Skipped (duplicates): %s, Errors: %s' % (migrated, skipped, errors)
            
            # Reload form to show updated count (keep popup open)
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'views': [(False, 'form')],
                'context': {
                    'migration_message': message,
                    'migration_migrated': migrated,
                    'migration_skipped': skipped,
                    'migration_errors': errors,
                }
            }
        except UserError:
            raise
        except Exception as e:
            _logger.error("Error migrating customers: %s" % str(e))
            raise UserError('Error migrating customers: %s' % str(e))
    
    def _prepare_customer_vals(self, customer_data):
        """Prepare customer values for creation"""
        # Handle country
        country = False
        country_id = customer_data.get('country_id')
        if country_id:
            country_id_val = country_id[0] if isinstance(country_id, list) else country_id
            if country_id_val:
                country = self.env['res.country'].browse(country_id_val)
                if not country.exists():
                    country = False
        
        # Handle state with cleaning
        state = False
        state_id = customer_data.get('state_id')
        if state_id:
            state_id_val = state_id[0] if isinstance(state_id, list) else state_id
            state_name = state_id[1] if isinstance(state_id, list) and len(state_id) > 1 else ''
            
            if state_id_val:
                state = self.env['res.country.state'].browse(state_id_val)
                if state.exists():
                    # Clean state name: remove (AE) and capitalize
                    if state_name:
                        cleaned_name = state_name.replace('(AE)', '').replace('(ae)', '').strip()
                        cleaned_name = ' '.join(word.capitalize() for word in cleaned_name.split())
                        # Update state name if it contains (AE)
                        if '(AE)' in state.name or '(ae)' in state.name:
                            state.write({'name': cleaned_name})
                else:
                    state = False
        
        # Build partner values, only including fields that exist in the model
        partner_vals = {
            'name': customer_data.get('name', ''),
            'email': customer_data.get('email', '') or False,
            'phone': customer_data.get('phone', '') or False,
            'street': customer_data.get('street', '') or False,
            'street2': customer_data.get('street2', '') or False,
            'city': customer_data.get('city', '') or False,
            'state_id': state.id if state else False,
            'zip': customer_data.get('zip', '') or False,
            'country_id': country.id if country else False,
            'vat': customer_data.get('vat', '') or False,
            'is_company': customer_data.get('is_company', False),
            'customer_rank': 1,  # Set as customer
        }
        
        # Only add mobile if the field exists in res.partner
        # Check if mobile field exists before adding it
        if 'mobile' in self.env['res.partner']._fields:
            mobile_value = customer_data.get('mobile', '') or False
            if mobile_value:
                partner_vals['mobile'] = mobile_value
        
        return partner_vals

    def action_refresh_view(self):
        """Simple view reload helper for the wizard buttons."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'views': [(False, 'form')],
        }

    # -------------------------------------------------------------------------
    # Export helpers for skipped / error quotations (CSV/Excel-friendly)
    # -------------------------------------------------------------------------

    def _export_quotation_log(self, log_field, filename):
        """Internal helper to export a text log field as CSV attachment."""
        self.ensure_one()
        data = (getattr(self, log_field) or '').strip()
        if not data:
            raise UserError('No data to export.')

        # Ensure we have bytes
        csv_bytes = data.encode('utf-8')
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(csv_bytes),
            'mimetype': 'text/csv',
            'res_model': self._name,
            'res_id': self.id,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=1' % attachment.id,
            'target': 'self',
        }

    def action_export_quotation_skipped(self):
        """Download skipped quotations report as CSV (Excel-friendly)."""
        return self._export_quotation_log('quotation_skipped_log', 'quotation_skipped.csv')

    def action_export_quotation_errors(self):
        """Download quotation errors report as CSV (Excel-friendly)."""
        return self._export_quotation_log('quotation_error_log', 'quotation_errors.csv')
    
    def action_migrate_quotations(self):
        """Migrate quotations from Odoo 14 to Odoo 19 in batches"""
        self.ensure_one()
        if self.quotations_count == 0:
            raise UserError('No quotations found. Please check data first.')
        if not self.config_id:
            raise UserError('Please select a migration configuration first.')

        batch_size = 30  # requested batch size
        migrated_total = self.quotations_migrated or 0
        skipped_total = 0
        errors_total = 0

        # mark as migrating
        if not self.is_migrating:
            self.write({
                'is_migrating': True,
                'migration_status': 'Starting quotation migration in batches of %s...' % batch_size,
            })
            self.env.cr.commit()

        try:
            from ..models.odoo14_api_client import Odoo14APIClient

            client = Odoo14APIClient(
                url=self.config_id.odoo14_url,
                db=self.config_id.odoo14_database,
                username=self.config_id.odoo14_username,
                password=self.config_id.odoo14_password
            )

            if not client.authenticate():
                raise UserError('Failed to authenticate with Odoo 14. Please test the connection first.')

            domain = []
            default_fields = [
                'name', 'partner_id', 'date_order', 'validity_date', 'amount_total',
                'amount_untaxed', 'amount_tax', 'state', 'pricelist_id', 'payment_term_id',
                'order_line', 'note', 'client_order_ref', 'user_id', 'team_id', 'company_id'
            ]

            fields_to_fetch = default_fields.copy()
            try:
                all_fields = client.fields_get('sale.order')
                if all_fields:
                    problematic_fields = ['due_amount', 'credit', 'debit', 'invoice_ids', 'invoice_count']
                    dynamic_fields = []
                    for f, field_info in all_fields.items():
                        field_type = field_info.get('type', '')
                        field_store = field_info.get('store', True)
                        if field_type in ('one2many', 'many2many') and f != 'order_line':
                            continue
                        if f in problematic_fields:
                            continue
                        if (not field_store and field_type not in ('char', 'text', 'integer', 'float', 'boolean', 'date', 'datetime')):
                            continue
                        dynamic_fields.append(f)
                    fields_to_fetch = list(set(fields_to_fetch + dynamic_fields))
                    _logger.info("Retrieved %s fields for sale.order migration", len(fields_to_fetch))
            except Exception as e:
                _logger.warning("Could not get all fields for migration using fields_get, using default set: %s", str(e))

            # process only ONE batch per call to avoid timeouts; user can click Continue
            # If a manual start number is provided (1‑based), use it when there is no offset yet
            if self.quotations_offset:
                offset = self.quotations_offset
            elif self.start_quotation_number and self.start_quotation_number > 1:
                offset = self.start_quotation_number - 1
            else:
                offset = migrated_total

            quotations = client.search_read(
                'sale.order',
                domain,
                fields_to_fetch,
                limit=batch_size,
                offset=offset,
                order='id'
            )

            if not quotations:
                # no more records
                self.write({
                    'is_migrating': False,
                    'migration_status': 'Migration complete! Migrated: %s, Skipped: %s, Errors: %s' % (
                        migrated_total, skipped_total, errors_total
                    )
                })
                self.env.cr.commit()
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': self._name,
                    'res_id': self.id,
                    'view_mode': 'form',
                    'target': 'new',
                    'views': [(False, 'form')],
                }

            batch_migrated = 0
            batch_skipped = 0
            batch_errors = 0
            skipped_lines = []
            error_lines = []

            for quotation_data in quotations:
                try:
                    quotation_name = quotation_data.get('name', '').strip()
                    if quotation_name:
                        existing = self.env['sale.order'].search([('name', '=', quotation_name)], limit=1)
                        if existing:
                            batch_skipped += 1
                            skipped_lines.append('%s,"Already exists in Odoo 19"' % (quotation_name.replace('"', '""') or ''))
                            continue

                    quotation_vals = self._prepare_quotation_vals(quotation_data, client)
                    quotation = self.env['sale.order'].create(quotation_vals)

                    # Preserve original creation date from Odoo 14 if available
                    src_create_date = quotation_data.get('create_date')
                    if src_create_date:
                        try:
                            # Force create_date (and align write_date) at SQL level
                            self.env.cr.execute(
                                """
                                UPDATE sale_order
                                   SET create_date = %s,
                                       write_date = COALESCE(write_date, %s)
                                 WHERE id = %s
                                """,
                                (src_create_date, src_create_date, quotation.id),
                            )
                        except Exception as e:
                            _logger.warning(
                                "Could not set original create_date for quotation %s: %s",
                                quotation.name,
                                str(e),
                            )

                    self._create_quotation_lines(quotation, quotation_data, client)

                    self.env.cr.commit()
                    batch_migrated += 1
                except Exception as e:
                    try:
                        if not self.env.cr.closed:
                            self.env.cr.rollback()
                    except Exception as rollback_error:
                        _logger.error("Error during rollback: %s", rollback_error)
                    batch_errors += 1
                    q_name = quotation_data.get('name', 'Unknown') or ''
                    err_msg = str(e).replace('"', '""')
                    error_lines.append('%s,"%s"' % (q_name, err_msg))
                    _logger.error("Error migrating quotation %s: %s", q_name, str(e))
                    continue

            migrated_total += batch_migrated
            skipped_total += batch_skipped
            errors_total += batch_errors
            offset += len(quotations)

            # append to CSV-style logs (with header once)
            if skipped_lines:
                header = 'name,reason'
                existing = (self.quotation_skipped_log or '').strip()
                if not existing:
                    new_text = header + '\n' + '\n'.join(skipped_lines)
                else:
                    new_text = existing + '\n' + '\n'.join(skipped_lines)
                self.quotation_skipped_log = new_text

            if error_lines:
                header = 'name,error'
                existing = (self.quotation_error_log or '').strip()
                if not existing:
                    new_text = header + '\n' + '\n'.join(error_lines)
                else:
                    new_text = existing + '\n' + '\n'.join(error_lines)
                self.quotation_error_log = new_text

            progress_pct = (migrated_total / self.quotations_count * 100) if self.quotations_count else 0
            self.write({
                'quotations_migrated': migrated_total,
                'quotations_offset': offset,
                'migration_status': 'Migrated %s/%s quotations (%.1f%%). Last batch: %s migrated, %s skipped, %s errors.' % (
                    migrated_total, self.quotations_count, progress_pct, batch_migrated, batch_skipped, batch_errors
                )
            })
            self.env.cr.commit()

            # if not finished, stay in migrating state; user can click Continue Migration
            if migrated_total >= self.quotations_count or offset >= self.quotations_count:
                self.write({
                    'is_migrating': False,
                    'migration_status': 'Migration complete! Migrated: %s, Skipped: %s, Errors: %s' % (
                        migrated_total, skipped_total, errors_total
                    )
                })
                self.env.cr.commit()

            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'views': [(False, 'form')],
            }

        except UserError:
            raise
        except Exception as e:
            _logger.error("Error migrating quotations: %s", str(e))
            raise UserError('Error migrating quotations: %s' % str(e))
    
    def _prepare_quotation_vals(self, quotation_data, client):
        """Prepare quotation values for creation"""
        # Get or create partner - REQUIRED for quotation
        partner = False
        partner_id = quotation_data.get('partner_id')
        if partner_id:
            partner_id_val = partner_id[0] if isinstance(partner_id, list) else partner_id
            partner_name = partner_id[1] if isinstance(partner_id, list) and len(partner_id) > 1 else ''
            
            if partner_id_val:
                try:
                    # First try to find by ID
                    partner = self.env['res.partner'].browse(partner_id_val)
                    if not partner.exists():
                        partner = False
                except:
                    partner = False
                
                # If not found by ID, try by name
                if not partner and partner_name:
                    try:
                        partner = self.env['res.partner'].search([
                            ('name', '=', partner_name)
                        ], limit=1)
                    except Exception as e:
                        _logger.warning("Error searching for partner by name %s: %s" % (partner_name, str(e)))
                        partner = False
                
                # If still not found, try to get from Odoo 14 and create
                if not partner:
                    try:
                        partner_data = client.get_partner(partner_id_val)
                        if partner_data:
                            # Use the same logic as customer migration
                            partner_vals = self._prepare_customer_vals(partner_data)
                            partner = self.env['res.partner'].create(partner_vals)
                    except Exception as e:
                        _logger.warning("Error creating partner %s: %s" % (partner_id_val, str(e)))
                        partner = False
        
        # Partner is REQUIRED - if we don't have one, we can't create the quotation
        if not partner:
            raise ValueError("Partner is required but not found or could not be created for quotation %s" % quotation_data.get('name', 'Unknown'))
        
        # Get pricelist
        pricelist = False
        pricelist_id = quotation_data.get('pricelist_id')
        if pricelist_id:
            pricelist_id_val = pricelist_id[0] if isinstance(pricelist_id, list) else pricelist_id
            if pricelist_id_val:
                pricelist = self.env['product.pricelist'].browse(pricelist_id_val)
                if not pricelist.exists():
                    pricelist = False
        
        # Get payment terms
        payment_term = False
        payment_term_id = quotation_data.get('payment_term_id')
        if payment_term_id:
            payment_term_id_val = payment_term_id[0] if isinstance(payment_term_id, list) else payment_term_id
            if payment_term_id_val:
                payment_term = self.env['account.payment.term'].browse(payment_term_id_val)
                if not payment_term.exists():
                    payment_term = False
        
        # Standard fields
        # In Odoo 19, partner_invoice_id and partner_shipping_id are required (NOT NULL)
        # We already checked that partner exists above, so partner.id should be valid
        partner_id_val = partner.id
        
        # Always set salesperson to Administrator
        admin_user = self.env.ref('base.user_root')
        
        quotation_vals = {
            'name': quotation_data.get('name', ''),
            'partner_id': partner_id_val,
            'partner_invoice_id': partner_id_val,  # Required in Odoo 19 - always use partner_id
            'partner_shipping_id': partner_id_val,  # Required in Odoo 19 - always use partner_id
            'date_order': quotation_data.get('date_order', False),
            'validity_date': quotation_data.get('validity_date', False),
            'pricelist_id': pricelist.id if pricelist else False,
            'payment_term_id': payment_term.id if payment_term else False,
            'state': 'draft',  # Always create as draft
            'client_order_ref': quotation_data.get('client_order_ref', ''),
            'note': quotation_data.get('note', ''),
            'user_id': admin_user.id,  # Always set to Administrator
        }
        
        # Override with specific invoice/shipping addresses if provided in quotation data
        # But ensure we always have a valid value (fallback to partner_id if override fails)
        if quotation_data.get('partner_invoice_id'):
            invoice_partner_id = quotation_data.get('partner_invoice_id')
            invoice_partner_id_val = invoice_partner_id[0] if isinstance(invoice_partner_id, list) else invoice_partner_id
            if invoice_partner_id_val:
                invoice_partner = self.env['res.partner'].browse(invoice_partner_id_val)
                if invoice_partner.exists():
                    quotation_vals['partner_invoice_id'] = invoice_partner_id_val
                # If override partner doesn't exist, keep the default (partner_id_val)
        
        if quotation_data.get('partner_shipping_id'):
            shipping_partner_id = quotation_data.get('partner_shipping_id')
            shipping_partner_id_val = shipping_partner_id[0] if isinstance(shipping_partner_id, list) else shipping_partner_id
            if shipping_partner_id_val:
                shipping_partner = self.env['res.partner'].browse(shipping_partner_id_val)
                if shipping_partner.exists():
                    quotation_vals['partner_shipping_id'] = shipping_partner_id_val
                # If override partner doesn't exist, keep the default (partner_id_val)
        
        # Final safety check - ensure both are set (should never be False at this point)
        if not quotation_vals.get('partner_invoice_id'):
            quotation_vals['partner_invoice_id'] = partner_id_val
        if not quotation_vals.get('partner_shipping_id'):
            quotation_vals['partner_shipping_id'] = partner_id_val
        
        # Add all custom fields (fields not in standard list)
        # Include fields from fm_amc_crm_custom and fm_amc_estimation modules
        standard_field_names = [
            'id', 'name', 'partner_id', 'date_order', 'validity_date',
            'pricelist_id', 'payment_term_id', 'order_line', 'note',
            'client_order_ref', 'state', 'amount_total', 'amount_untaxed',
            'amount_tax', 'user_id', 'team_id', 'company_id',
            'create_date', 'write_date', 'create_uid', 'write_uid',
            '__last_update',
            # Required fields that should not be overwritten by custom field processing
            'partner_invoice_id', 'partner_shipping_id',  # Required in Odoo 19, already set above
            # Computed fields that should be skipped (from fm_amc_crm_custom)
            'estimated_value',  # Computed, not stored
            'is_draft_stage', 'is_pending_approval_stage', 'is_quotation_stage',
            'is_quotation_sent_stage', 'is_sales_order_stage', 'is_declined_stage',
            'is_cancelled_stage', 'is_locked',  # All computed, not stored
        ]
        
        # Add custom fields to quotation_vals (from fm_amc_crm_custom, fm_amc_estimation, etc.)
        # Only include fields that exist in Odoo 19 and are not computed/readonly
        sale_order_fields = self.env['sale.order']._fields
        for key, value in quotation_data.items():
            if key not in standard_field_names and not key.startswith('__'):
                # Skip user_id - always use Administrator
                if key == 'user_id':
                    continue
                
                # Check if field exists in Odoo 19
                if key in sale_order_fields:
                    field = sale_order_fields[key]
                    
                    # Skip computed fields that are not stored
                    if hasattr(field, 'compute') and field.compute and not field.store:
                        continue
                    
                    # Skip readonly fields
                    if hasattr(field, 'readonly') and field.readonly:
                        continue
                    
                    try:
                        # Handle Many2one fields (convert from [id, name] to id)
                        if field.type == 'many2one':
                            if isinstance(value, list) and len(value) > 0:
                                # Check if the related record exists
                                related_model = self.env[field.comodel_name]
                                related_id = value[0] if value[0] else False
                                if related_id and related_model.browse(related_id).exists():
                                    quotation_vals[key] = related_id
                                else:
                                    quotation_vals[key] = False
                            elif not value:
                                quotation_vals[key] = False
                            else:
                                quotation_vals[key] = value
                        # Handle Many2many fields (e.g., consultants_ids from fm_amc_crm_custom)
                        elif field.type == 'many2many':
                            if isinstance(value, list) and value:
                                # Extract IDs from Many2many format: [(6, 0, [ids])] or [id1, id2, ...]
                                many2many_ids = []
                                for item in value:
                                    if isinstance(item, (list, tuple)) and len(item) >= 3:
                                        # Format: (6, 0, [ids])
                                        if item[0] == 6 and isinstance(item[2], list):
                                            many2many_ids.extend(item[2])
                                        elif item[0] == 4:  # Link existing
                                            many2many_ids.append(item[1])
                                        elif item[0] == 5:  # Unlink all
                                            many2many_ids = []
                                    elif isinstance(item, int):
                                        many2many_ids.append(item)
                                
                                # Check if all IDs exist in target model
                                if many2many_ids:
                                    related_model = self.env[field.comodel_name]
                                    existing_ids = related_model.browse(many2many_ids).exists().ids
                                    if existing_ids:
                                        quotation_vals[key] = [(6, 0, existing_ids)]
                                    else:
                                        quotation_vals[key] = [(5, 0, 0)]  # Unlink all if none exist
                                else:
                                    quotation_vals[key] = [(5, 0, 0)]  # Unlink all
                            else:
                                quotation_vals[key] = [(5, 0, 0)]  # Unlink all if empty
                        # Handle One2many fields - skip (already handled separately)
                        elif field.type == 'one2many':
                            continue
                        # Handle text fields
                        elif field.type in ('char', 'text', 'html'):
                            if value:
                                quotation_vals[key] = str(value) if value else False
                            else:
                                quotation_vals[key] = False
                        # Handle numeric fields
                        elif field.type in ('integer', 'float'):
                            if value is not None:
                                try:
                                    quotation_vals[key] = float(value) if field.type == 'float' else int(value)
                                except (ValueError, TypeError):
                                    quotation_vals[key] = 0 if field.type == 'integer' else 0.0
                            else:
                                quotation_vals[key] = 0 if field.type == 'integer' else 0.0
                        # Handle boolean fields
                        elif field.type == 'boolean':
                            quotation_vals[key] = bool(value) if value else False
                        # Handle date fields
                        elif field.type == 'date':
                            if value:
                                quotation_vals[key] = value
                            else:
                                quotation_vals[key] = False
                        # Handle datetime fields
                        elif field.type == 'datetime':
                            if value:
                                quotation_vals[key] = value
                            else:
                                quotation_vals[key] = False
                        # Handle selection fields
                        elif field.type == 'selection':
                            if value and value in [sel[0] for sel in (field.selection or [])]:
                                quotation_vals[key] = value
                        # Handle other field types
                        else:
                            quotation_vals[key] = value
                    except Exception as e:
                        # Skip field if there's an error setting it
                        _logger.warning("Skipping field %s due to error: %s" % (key, str(e)))
                        continue
        
        # Final safety check - ensure required fields are always set (protect against overwrites)
        # This is critical because partner_invoice_id and partner_shipping_id are NOT NULL in Odoo 19
        if not quotation_vals.get('partner_invoice_id') or quotation_vals.get('partner_invoice_id') is False:
            quotation_vals['partner_invoice_id'] = partner_id_val
            _logger.warning("partner_invoice_id was missing/False, setting to partner_id: %s" % partner_id_val)
        if not quotation_vals.get('partner_shipping_id') or quotation_vals.get('partner_shipping_id') is False:
            quotation_vals['partner_shipping_id'] = partner_id_val
            _logger.warning("partner_shipping_id was missing/False, setting to partner_id: %s" % partner_id_val)
        
        return quotation_vals
    
    def _create_quotation_lines(self, quotation, quotation_data, client):
        """Create order lines for quotation"""
        order_line_ids = quotation_data.get('order_line', [])
        if not order_line_ids:
            return
        
        # Get order line IDs
        line_ids = []
        for line_id in order_line_ids:
            if isinstance(line_id, int):
                line_ids.append(line_id)
            elif isinstance(line_id, (list, tuple)) and len(line_id) > 0:
                line_ids.append(line_id[0])
        
        if not line_ids:
            return
        
        # Fetch order lines data
        if line_ids:
            order_lines_data = client.read('sale.order.line', line_ids, [
                'product_id', 'name', 'product_uom_qty', 'product_uom', 
                'price_unit', 'discount', 'tax_id', 'sequence', 'display_type'
            ])
        else:
            order_lines_data = []
        
        for line_data in order_lines_data:
            try:
                # Skip section/note lines
                if line_data.get('display_type') in ('line_section', 'line_note'):
                    continue
                
                # Get or create product
                product = False
                product_id = line_data.get('product_id')
                if product_id:
                    product_id_val = product_id[0] if isinstance(product_id, list) else product_id
                    if product_id_val:
                        product = self.env['product.product'].browse(product_id_val)
                        if not product.exists():
                            # Try to get product data from Odoo 14 and create
                            product_data = client.get_product(product_id_val)
                            if product_data:
                                # Search for existing product by default_code or name
                                existing_product = self.env['product.product'].search([
                                    '|',
                                    ('default_code', '=', product_data.get('default_code', '')),
                                    ('name', '=', product_data.get('name', ''))
                                ], limit=1)
                                
                                if existing_product:
                                    product = existing_product
                                else:
                                    # Create product template first, then product
                                    # Map product type from Odoo 14 to Odoo 19
                                    product_type = product_data.get('type', 'consu')
                                    # In Odoo 19, valid types are: 'consu', 'service', 'product' (storable)
                                    # Ensure we use valid type - check what's actually available in Odoo 19
                                    try:
                                        # Get the selection field values for type
                                        product_template_model = self.env['product.template']
                                        type_field = product_template_model._fields.get('type')
                                        if type_field and hasattr(type_field, 'selection'):
                                            valid_types = [v[0] for v in type_field.selection]
                                            if product_type not in valid_types:
                                                # Default to first valid type if current type is invalid
                                                product_type = valid_types[0] if valid_types else 'consu'
                                                _logger.warning("Product type '%s' not valid in Odoo 19, using '%s' instead" % (
                                                    product_data.get('type', 'unknown'), product_type
                                                ))
                                    except Exception as e:
                                        # If we can't check, default to 'consu'
                                        if product_type not in ('consu', 'service', 'product'):
                                            product_type = 'consu'
                                        _logger.warning("Could not validate product type, using '%s': %s" % (product_type, str(e)))
                                    
                                    # Get UoM if provided
                                    uom_id = False
                                    if product_data.get('uom_id'):
                                        uom_id_val = product_data.get('uom_id')
                                        uom_id_val = uom_id_val[0] if isinstance(uom_id_val, list) else uom_id_val
                                        if uom_id_val:
                                            uom = self.env['uom.uom'].browse(uom_id_val)
                                            if uom.exists():
                                                uom_id = uom_id_val
                                    
                                    # Create product template
                                    template_vals = {
                                        'name': product_data.get('name', 'Product'),
                                        'default_code': product_data.get('default_code', ''),
                                        'list_price': product_data.get('list_price', 0.0),
                                        'type': product_type,
                                        'sale_ok': product_data.get('sale_ok', True),
                                        'purchase_ok': product_data.get('purchase_ok', False),
                                    }
                                    if uom_id:
                                        template_vals['uom_id'] = uom_id
                                    
                                    try:
                                        product_template = self.env['product.template'].create(template_vals)
                                        # Get the product variant
                                        product = product_template.product_variant_id
                                    except Exception as e:
                                        _logger.error("Error creating product template for %s: %s" % (
                                            product_data.get('name', 'Unknown'), str(e)
                                        ))
                                        # Try with default type if creation failed
                                        if template_vals.get('type') != 'consu':
                                            template_vals['type'] = 'consu'
                                            try:
                                                product_template = self.env['product.template'].create(template_vals)
                                                product = product_template.product_variant_id
                                            except Exception as e2:
                                                _logger.error("Error creating product template with default type: %s" % str(e2))
                                                product = False
                                        else:
                                            product = False
                
                # Get UoM - in Odoo 19, the field is product_uom_id (not product_uom)
                uom = False
                product_uom = line_data.get('product_uom')
                if product_uom:
                    uom_id_val = product_uom[0] if isinstance(product_uom, list) else product_uom
                    if uom_id_val:
                        uom = self.env['uom.uom'].browse(uom_id_val)
                        if not uom.exists():
                            uom = False
                
                # If no UoM from line data, use product's default UoM
                if not uom and product:
                    uom = product.uom_id
                
                # Get taxes
                # In Odoo 19, check if tax_id field exists (it should be tax_id for Many2many)
                taxes = self.env['account.tax']
                tax_ids = line_data.get('tax_id', [])
                if tax_ids:
                    tax_id_list = []
                    for tax_id in tax_ids:
                        if isinstance(tax_id, int):
                            tax_id_list.append(tax_id)
                        elif isinstance(tax_id, (list, tuple)) and len(tax_id) > 0:
                            tax_id_list.append(tax_id[0])
                    
                    if tax_id_list:
                        taxes = self.env['account.tax'].browse(tax_id_list)
                        taxes = taxes.filtered(lambda t: t.exists())
                
                # Create order line
                # In Odoo 19, the field is product_uom_id (not product_uom)
                line_vals = {
                    'order_id': quotation.id,
                    'product_id': product.id if product else False,
                    'name': line_data.get('name', '') or (product.name if product else ''),
                    'product_uom_qty': line_data.get('product_uom_qty', 1.0),
                    'product_uom_id': uom.id if uom else False,  # Fixed: use product_uom_id in Odoo 19
                    'price_unit': line_data.get('price_unit', 0.0),
                    'discount': line_data.get('discount', 0.0),
                    'sequence': line_data.get('sequence', 10),
                }
                
                # Check if tax_id field exists in sale.order.line before setting it
                # In Odoo 19, the field should be tax_id, but let's verify it exists
                sale_order_line_fields = self.env['sale.order.line']._fields
                tax_field_name = None
                if 'tax_id' in sale_order_line_fields:
                    tax_field_name = 'tax_id'
                elif 'tax_ids' in sale_order_line_fields:
                    tax_field_name = 'tax_ids'
                
                if taxes and tax_field_name:
                    line_vals[tax_field_name] = [(6, 0, taxes.ids)]
                elif taxes:
                    _logger.warning("Tax field not found in sale.order.line (checked tax_id, tax_ids), skipping tax assignment. Available tax fields: %s" % 
                                  [f for f in sale_order_line_fields.keys() if 'tax' in f.lower()])
                
                try:
                    self.env['sale.order.line'].create(line_vals)
                except Exception as e:
                    # If creation fails due to tax field, try without taxes
                    if 'tax' in str(e).lower() and tax_field_name and tax_field_name in line_vals:
                        _logger.warning("Error creating order line with taxes, retrying without taxes: %s" % str(e))
                        del line_vals[tax_field_name]
                        self.env['sale.order.line'].create(line_vals)
                    else:
                        raise
                
            except Exception as e:
                _logger.error("Error creating order line: %s" % str(e))
                continue
    
    def action_migrate_sales_orders(self):
        """Migrate sales orders"""
        if self.sales_orders_count == 0:
            raise UserError('No sales orders found. Please check data first.')
        # TODO: Implement migration
        return {'type': 'ir.actions.act_window_close'}
    
    def action_migrate_invoices(self):
        """Migrate invoices"""
        if self.invoices_count == 0:
            raise UserError('No invoices found. Please check data first.')
        # TODO: Implement migration
        return {'type': 'ir.actions.act_window_close'}
    
    def _initialize_items(self):
        """Initialize default customer migration items - not needed for fixed layout"""
        pass
    
    @api.model
    def default_get(self, fields_list):
        """Initialize default customer migration items"""
        res = super().default_get(fields_list)
        return res

