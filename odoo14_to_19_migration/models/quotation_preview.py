# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class QuotationPreview(models.TransientModel):
    _name = 'odoo14.quotation.preview'
    _description = 'Odoo 14 Quotation Preview'

    wizard_id = fields.Many2one(
        'odoo14.customer.migration.wizard',
        string='Migration Wizard',
        required=True,
        ondelete='cascade'
    )
    
    config_id = fields.Many2one(
        'odoo14.migration.config',
        string='Migration Configuration',
        required=True
    )
    
    current_index = fields.Integer(string='Current Index', default=0)
    total_count = fields.Integer(string='Total Count', default=0)
    
    # Computed field for display
    display_position = fields.Char(
        string='Position',
        compute='_compute_display_position',
        store=False,
        readonly=True
    )
    
    @api.depends('current_index', 'total_count')
    def _compute_display_position(self):
        for rec in self:
            if rec.total_count > 0:
                rec.display_position = 'Quotation %s of %s' % (rec.current_index + 1, rec.total_count)
            else:
                rec.display_position = 'No Quotations'

    # Quotation fields
    quotation_name = fields.Char(string='Quotation Number', readonly=True)
    partner_name = fields.Char(string='Customer', readonly=True)
    date_order = fields.Datetime(string='Order Date', readonly=True)
    validity_date = fields.Date(string='Expiration Date', readonly=True)
    amount_total = fields.Float(string='Total Amount', readonly=True)
    amount_untaxed = fields.Float(string='Untaxed Amount', readonly=True)
    amount_tax = fields.Float(string='Tax Amount', readonly=True)
    state = fields.Char(string='State', readonly=True)
    pricelist_id = fields.Char(string='Pricelist', readonly=True)
    payment_term_id = fields.Char(string='Payment Terms', readonly=True)
    quotation_data_json = fields.Text(string='Full Quotation Data (JSON)', readonly=True)
    custom_fields_json = fields.Text(string='Custom Fields (JSON)', readonly=True)
    
    # Order lines
    order_line_ids = fields.One2many(
        'odoo14.quotation.line.preview',
        'preview_id',
        string='Order Lines',
        readonly=True
    )
    
    def _load_quotation(self, offset=0):
        """Load quotation data from Odoo 14"""
        self.ensure_one()
        try:
            from ..models.odoo14_api_client import Odoo14APIClient
            
            client = Odoo14APIClient(
                url=self.config_id.odoo14_url,
                db=self.config_id.odoo14_database,
                username=self.config_id.odoo14_username,
                password=self.config_id.odoo14_password
            )
            
            if not client.authenticate():
                raise UserError('Failed to authenticate with Odoo 14.')
            
            # Try to check if sale.order model exists, but don't fail if check fails
            # We'll try to use it anyway and catch the error if it doesn't exist
            model_exists = client.check_model_exists('sale.order')
            if not model_exists:
                _logger.warning("Model 'sale.order' check returned False, but will attempt to use it anyway")
            
            # Get quotation at offset with ALL fields (including custom fields)
            # Get all quotations regardless of state
            domain = []
            
            # Get all fields for sale.order model (including custom fields)
            # Use standard fields as default
            default_fields = [
                'name', 'partner_id', 'date_order', 'validity_date', 
                'amount_total', 'amount_untaxed', 'amount_tax', 'state',
                'pricelist_id', 'payment_term_id', 'order_line', 'note',
                'client_order_ref', 'user_id', 'team_id', 'company_id'
            ]
            
            # Try to get all fields dynamically, but don't fail if it doesn't work
            fields_to_fetch = default_fields.copy()
            try:
                all_fields = client.fields_get('sale.order')
                if all_fields:
                    # Exclude problematic fields:
                    # - One2many/Many2many (except order_line which we need)
                    # - Computed fields that require request context (store=False and computed)
                    # - Fields that might cause CacheMiss errors
                    problematic_fields = ['due_amount', 'credit', 'debit', 'invoice_ids', 'invoice_count']
                    dynamic_fields = []
                    for f, field_info in all_fields.items():
                        field_type = field_info.get('type', '')
                        field_store = field_info.get('store', True)
                        # Skip One2many/Many2many except order_line
                        if field_type in ('one2many', 'many2many') and f != 'order_line':
                            continue
                        # Skip problematic computed fields
                        if f in problematic_fields:
                            continue
                        # Skip computed fields that are not stored (they might require request context)
                        if not field_store and field_type not in ('char', 'text', 'integer', 'float', 'boolean', 'date', 'datetime'):
                            continue
                        dynamic_fields.append(f)
                    
                    # Merge with default fields, removing duplicates
                    fields_to_fetch = list(set(fields_to_fetch + dynamic_fields))
                    _logger.info("Successfully retrieved %s fields for sale.order (excluding problematic computed fields)" % len(fields_to_fetch))
            except Exception as e:
                # If fields_get fails, just use default fields - don't raise error
                _logger.warning("Could not get all fields using fields_get, using default set: %s" % str(e))
                # Continue with default_fields
            
            # First verify we can access the model by checking count
            # This helps distinguish between "model doesn't exist" and "no records found"
            try:
                test_count = client.count('sale.order', domain)
                _logger.info("Verified access to sale.order - count: %s" % test_count)
            except Exception as e:
                error_msg = str(e).lower()
                if "not found" in error_msg or "doesn't exist" in error_msg:
                    raise UserError('Model "sale.order" not found in Odoo 14. Please ensure the "sale" module is installed and you have proper access rights.')
                elif "access" in error_msg or "permission" in error_msg or "not allowed" in error_msg:
                    raise UserError('Access denied to sale.order. Please check user permissions in Odoo 14. The user needs read access to sale.order model.')
                else:
                    raise UserError('Error accessing sale.order: %s' % str(e))
            
            # Now try to get quotations with the domain
            # First try with all fields, if that fails try with basic fields only
            quotations = []
            try:
                quotations = client.search_read('sale.order', domain, 
                    fields_to_fetch, 
                    limit=1, offset=offset, order='id')
            except Exception as e:
                error_msg = str(e).lower()
                _logger.warning("Error with full field list, trying with basic fields only: %s" % str(e))
                
                # Try with just basic fields as fallback
                basic_fields = ['id', 'name', 'partner_id', 'date_order', 'state', 'amount_total']
                try:
                    quotations = client.search_read('sale.order', domain, 
                        basic_fields, 
                        limit=1, offset=offset, order='id')
                    _logger.info("Successfully loaded quotation with basic fields only")
                except Exception as e2:
                    error_msg2 = str(e2).lower()
                    # If basic fields also fail, it's a real access issue
                    if "not found" in error_msg2 or "doesn't exist" in error_msg2:
                        raise UserError('Cannot read sale.order records. Model exists but search_read failed. Please check user access rights in Odoo 14.')
                    elif "access" in error_msg2 or "permission" in error_msg2:
                        raise UserError('Access denied when reading sale.order records. Please check user permissions in Odoo 14.')
                    # Re-raise the original error
                    raise UserError('Error reading sale.order: %s' % str(e))
            
            # If no quotations found, try alternative approaches
            if not quotations:
                _logger.warning("No quotation found at offset %s with domain %s. Trying alternative approaches..." % (offset, domain))
                try:
                    # First, verify the total count
                    total_count = client.count('sale.order', domain)
                    _logger.info("Total quotations matching domain %s: %s" % (domain, total_count))
                    
                    if total_count == 0:
                        # Try with a broader domain to see if any quotations exist
                        _logger.info("No quotations with domain %s. Trying without state filter..." % domain)
                        broader_domain = []
                        broader_count = client.count('sale.order', broader_domain)
                        if broader_count > 0:
                            raise UserError('No quotations found in "draft" or "sent" state. Total quotations: %s. Please check the state filter.' % broader_count)
                        else:
                            raise UserError('No quotations found in Odoo 14. Please ensure quotations exist and you have proper access rights.')
                    
                    if offset >= total_count:
                        raise UserError('Quotation index %s is out of range. Total quotations: %s' % (offset + 1, total_count))
                    
                    # Try alternative approach: get IDs first, then read
                    _logger.info("Trying alternative approach: getting IDs first (offset=%s, total=%s)..." % (offset, total_count))
                    quotation_ids = client.search('sale.order', domain, limit=total_count, offset=0, order='id')
                    _logger.info("Found %s quotation IDs" % len(quotation_ids))
                    
                    if quotation_ids and offset < len(quotation_ids):
                        # Read the specific quotation by ID
                        quotation_id = quotation_ids[offset]
                        _logger.info("Reading quotation ID: %s" % quotation_id)
                        quotation_data = client.read('sale.order', [quotation_id], fields_to_fetch)
                        if quotation_data:
                            quotations = quotation_data  # read already returns a list
                            _logger.info("Successfully read quotation using alternative method")
                        else:
                            raise UserError('Could not read quotation data for ID %s' % quotation_id)
                    else:
                        raise UserError('Quotation index %s is out of range. Found %s quotations.' % (offset, len(quotation_ids)))
                        
                except UserError:
                    raise
                except Exception as e:
                    _logger.error("Error getting quotation: %s" % str(e))
                    error_msg = str(e).lower()
                    if "not found" in error_msg or "access denied" in error_msg:
                        raise UserError('Cannot access sale.order. Please check that the "sale" module is installed and you have proper access rights in Odoo 14.')
                    raise UserError('No quotation found at this position. Error: %s' % str(e))
            
            if not quotations:
                raise UserError('No quotation found at this position.')
            
            quotation = quotations[0]
            quotation_id = quotation.get('id')
            
            # Get partner name
            partner_name = ''
            if quotation.get('partner_id'):
                partner_data = quotation.get('partner_id')
                if isinstance(partner_data, (list, tuple)) and len(partner_data) > 1:
                    partner_name = partner_data[1]
            
            # Get pricelist name
            pricelist_name = ''
            if quotation.get('pricelist_id'):
                pricelist_data = quotation.get('pricelist_id')
                if isinstance(pricelist_data, (list, tuple)) and len(pricelist_data) > 1:
                    pricelist_name = pricelist_data[1]
            
            # Get payment terms name
            payment_term_name = ''
            if quotation.get('payment_term_id'):
                payment_term_data = quotation.get('payment_term_id')
                if isinstance(payment_term_data, (list, tuple)) and len(payment_term_data) > 1:
                    payment_term_name = payment_term_data[1]
            
            # Get order lines
            order_line_ids = quotation.get('order_line', [])
            if isinstance(order_line_ids, list) and order_line_ids:
                # Fetch order line details
                line_ids = [line_id if isinstance(line_id, int) else line_id[0] if isinstance(line_id, (list, tuple)) else line_id 
                           for line_id in order_line_ids]
                
                # Get order lines data
                if line_ids:
                    order_lines_data = client.read('sale.order.line', line_ids, [
                        'product_id', 'name', 'product_uom_qty', 'product_uom', 
                        'price_unit', 'discount', 'price_subtotal', 'tax_id', 'sequence'
                    ])
                else:
                    order_lines_data = []
            else:
                order_lines_data = []
            
            # Clear existing lines
            self.order_line_ids.unlink()
            
            # Create order line previews
            line_previews = []
            for line_data in order_lines_data:
                # Get product name
                product_name = ''
                if line_data.get('product_id'):
                    product_data = line_data.get('product_id')
                    if isinstance(product_data, (list, tuple)) and len(product_data) > 1:
                        product_name = product_data[1]
                
                # Get UoM name
                uom_name = ''
                if line_data.get('product_uom'):
                    uom_data = line_data.get('product_uom')
                    if isinstance(uom_data, (list, tuple)) and len(uom_data) > 1:
                        uom_name = uom_data[1]
                
                # Get tax names
                tax_names = []
                if line_data.get('tax_id'):
                    tax_ids = line_data.get('tax_id')
                    if isinstance(tax_ids, list):
                        tax_id_list = []
                        for tax_id in tax_ids:
                            if isinstance(tax_id, int):
                                tax_id_list.append(tax_id)
                            elif isinstance(tax_id, (list, tuple)) and len(tax_id) > 0:
                                tax_id_list.append(tax_id[0])
                        
                        if tax_id_list:
                            tax_data_list = client.read('account.tax', tax_id_list, ['name'])
                            for tax_data in tax_data_list:
                                tax_names.append(tax_data.get('name', ''))
                
                line_previews.append({
                    'preview_id': self.id,
                    'sequence': line_data.get('sequence', 10),
                    'product_name': product_name,
                    'name': line_data.get('name', ''),
                    'product_uom_qty': line_data.get('product_uom_qty', 0.0),
                    'product_uom': uom_name,
                    'price_unit': line_data.get('price_unit', 0.0),
                    'discount': line_data.get('discount', 0.0),
                    'price_subtotal': line_data.get('price_subtotal', 0.0),
                    'tax_id': ', '.join(tax_names) if tax_names else '',
                })
            
            # Separate standard and custom fields
            standard_fields = [
                'id', 'name', 'partner_id', 'date_order', 'validity_date',
                'amount_total', 'amount_untaxed', 'amount_tax', 'state',
                'pricelist_id', 'payment_term_id', 'order_line', 'note',
                'client_order_ref', 'user_id', 'team_id', 'company_id',
                'create_date', 'write_date', 'create_uid', 'write_uid'
            ]
            
            custom_fields_data = {}
            for key, value in quotation.items():
                if key not in standard_fields and not key.startswith('__'):
                    custom_fields_data[key] = value
            
            # Update preview with quotation data
            self.write({
                'current_index': offset,
                'quotation_name': quotation.get('name', ''),
                'partner_name': partner_name,
                'date_order': quotation.get('date_order', False),
                'validity_date': quotation.get('validity_date', False),
                'amount_total': quotation.get('amount_total', 0.0),
                'amount_untaxed': quotation.get('amount_untaxed', 0.0),
                'amount_tax': quotation.get('amount_tax', 0.0),
                'state': quotation.get('state', ''),
                'pricelist_id': pricelist_name,
                'payment_term_id': payment_term_name,
                'quotation_data_json': str(quotation),  # Full data including all fields
                'custom_fields_json': str(custom_fields_data) if custom_fields_data else '',
                'order_line_ids': [(0, 0, line) for line in line_previews],
            })
            
            return True
        except Exception as e:
            _logger.error("Error loading quotation: %s" % str(e))
            raise UserError('Error loading quotation: %s' % str(e))
    
    def action_previous(self):
        """Navigate to previous quotation"""
        self.ensure_one()
        if self.current_index <= 0:
            raise UserError('This is the first quotation.')
        
        new_index = self.current_index - 1
        self._load_quotation(offset=new_index)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quotation Preview (%s of %s)' % (self.current_index + 1, self.total_count),
            'res_model': 'odoo14.quotation.preview',
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
        }
    
    def action_next(self):
        """Navigate to next quotation"""
        self.ensure_one()
        if self.current_index >= self.total_count - 1:
            raise UserError('This is the last quotation.')
        
        new_index = self.current_index + 1
        self._load_quotation(offset=new_index)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quotation Preview (%s of %s)' % (self.current_index + 1, self.total_count),
            'res_model': 'odoo14.quotation.preview',
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
        }

