# -*- coding: utf-8 -*-

import xmlrpc.client
import requests
import json
import logging
from datetime import datetime
from requests.auth import HTTPBasicAuth

_logger = logging.getLogger(__name__)


class Odoo14APIClient:
    """Client for connecting to Odoo 14 via XML-RPC API"""
    
    def __init__(self, url, db, username, password):
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        
        # Setup XML-RPC connections
        self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
        self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
    
    def authenticate(self):
        """Authenticate and get user ID"""
        try:
            self.uid = self.common.authenticate(self.db, self.username, self.password, {})
            if self.uid:
                _logger.info(f"Successfully authenticated to Odoo instance: {self.url}")
                return True
            else:
                _logger.error(f"Authentication failed for Odoo instance: {self.url}")
                return False
        except Exception as e:
            _logger.error(f"Authentication error: {str(e)}")
            return False
    
    def get_odoo_version(self):
        """Get the Odoo version of the connected instance"""
        try:
            version_info = self.common.version()
            server_version = version_info.get('server_version', 'Unknown')
            _logger.info(f"Connected to Odoo version: {server_version}")
            return server_version
        except Exception as e:
            _logger.warning(f"Could not determine Odoo version: {str(e)}")
            return None
    
    def check_model_exists(self, model_name):
        """Check if a model exists in the Odoo instance"""
        # Try to access the model directly first (more reliable)
        try:
            self.models.execute_kw(
                self.db, self.uid, self.password,
                model_name, 'search', [[]], {'limit': 1}
            )
            return True
        except Exception as e:
            error_msg = str(e).lower()
            # If it's an access error, the model exists but user can't access it
            if "access" in error_msg or "permission" in error_msg:
                _logger.warning("Model '%s' exists but user doesn't have access: %s" % (model_name, str(e)))
                return True  # Model exists, just no access
            # If it's a "doesn't exist" error, model doesn't exist
            if "doesn't exist" in error_msg or "not found" in error_msg:
                return False
            # For other errors, try ir.model as fallback
            try:
                result = self.models.execute_kw(
                    self.db, self.uid, self.password,
                    'ir.model', 'search', [[('model', '=', model_name)]]
                )
                return len(result) > 0
            except:
                # If all fails, assume model doesn't exist
                _logger.warning("Could not determine if model '%s' exists: %s" % (model_name, str(e)))
                return False
    
    def execute(self, model, method, args_list, kwargs_dict=None):
        """Execute a method on a model
        args_list: list of positional arguments to pass to the method
        kwargs_dict: dictionary of keyword arguments
        """
        if not self.uid:
            if not self.authenticate():
                raise Exception("Authentication failed")
        
        if kwargs_dict is None:
            kwargs_dict = {}
        
        try:
            return self.models.execute_kw(
                self.db, self.uid, self.password,
                model, method, args_list, kwargs_dict
            )
        except Exception as e:
            error_msg = str(e).lower()
            _logger.error(f"Error executing {model}.{method}: {str(e)}")
            
            # Check if it's an access/permission error vs model not found
            if "access" in error_msg or "permission" in error_msg or "not allowed" in error_msg:
                # Model exists but user doesn't have access
                raise Exception(f"Access denied to {model}.{method}. Please check user permissions in Odoo 14.")
            
            # Check if model doesn't exist
            if "doesn't exist" in error_msg or ("object" in error_msg and "not found" in error_msg):
                # Determine which module based on model name
                if 'sale.order' in model or 'sale' in model.lower():
                    module_name = "sale"
                elif 'account' in model.lower() or 'invoice' in model.lower():
                    module_name = "account"
                elif 'purchase' in model.lower():
                    module_name = "purchase"
                else:
                    module_name = "the required"
                raise Exception(f"Model '{model}' not found in Odoo 14. Please ensure the {module_name} module is installed and you have proper access rights.")
            
            # For other errors, re-raise as-is
            raise
    
    def search_read(self, model, domain, fields=None, limit=None, offset=0, order=None):
        """Search and read records"""
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        if limit:
            kwargs['limit'] = limit
        if offset:
            kwargs['offset'] = offset
        if order:
            kwargs['order'] = order
        
        try:
            return self.execute(model, 'search_read', [domain], kwargs)
        except Exception as e:
            error_msg = str(e).lower()
            # For model not found or access errors, re-raise so caller can handle appropriately
            # Don't silently return empty list - let caller decide what to do
            if "not found" in error_msg or "doesn't exist" in error_msg:
                _logger.warning("Model '%s' not found: %s" % (model, str(e)))
                # Re-raise with clearer message
                raise Exception("Model '%s' not found in Odoo 14. Please ensure the required module is installed." % model)
            elif "access denied" in error_msg or "access" in error_msg or "permission" in error_msg:
                _logger.warning("Access denied to '%s': %s" % (model, str(e)))
                raise Exception("Access denied to '%s'. Please check user permissions in Odoo 14." % model)
            # Re-raise other errors
            raise
    
    def search(self, model, domain, limit=None, offset=0, order=None):
        """Search records and return IDs"""
        kwargs = {}
        if limit:
            kwargs['limit'] = limit
        if offset:
            kwargs['offset'] = offset
        if order:
            kwargs['order'] = order
        return self.execute(model, 'search', [domain], kwargs)
    
    def count(self, model, domain):
        """Count records matching domain"""
        try:
            # search_count expects domain as a list argument
            # execute_kw signature: (db, uid, password, model, method, args, kwargs)
            # where args is a list containing the domain
            return self.execute(model, 'search_count', [domain], {})
        except Exception as e:
            error_msg = str(e).lower()
            _logger.error(f"Error counting {model}: {str(e)}")
            # Don't return 0 silently - re-raise so caller can handle it
            # The caller should check if model exists first
            raise
    
    def read(self, model, ids, fields=None):
        """Read records by IDs"""
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        return self.execute(model, 'read', [ids], kwargs)
    
    def fields_get(self, model, fields=None, attributes=None):
        """Get fields definition for a model"""
        try:
            kwargs = {}
            if fields:
                kwargs['fields'] = fields
            # Request store attribute to filter out non-stored computed fields
            if attributes:
                if isinstance(attributes, list):
                    if 'store' not in attributes:
                        attributes = list(attributes) + ['store']
                else:
                    attributes = [attributes, 'store']
            else:
                attributes = ['store']
            kwargs['attributes'] = attributes
            return self.execute(model, 'fields_get', [], kwargs)
        except Exception as e:
            # Don't re-raise with model not found error for fields_get
            # Just return None and let the caller handle it
            error_msg = str(e)
            if "doesn't exist" in error_msg.lower() or "object" in error_msg.lower():
                _logger.warning("Model '%s' not accessible for fields_get: %s" % (model, error_msg))
                return None
            # For other errors, re-raise
            raise
    
    def _get_invoice_model(self):
        """Detect which invoice model to use (account.invoice for Odoo 14, account.move for Odoo 15+)"""
        # Check version first
        version = self.get_odoo_version()
        if version:
            try:
                major_version = int(version.split('.')[0])
                if major_version == 14:
                    # Odoo 14 - try account.invoice first
                    if self.check_model_exists('account.invoice'):
                        return 'account.invoice'
                    elif self.check_model_exists('account.move'):
                        # Some Odoo 14 instances might use account.move
                        return 'account.move'
                elif major_version >= 15:
                    return 'account.move'
            except:
                pass
        
        # Fallback: check model existence
        if self.check_model_exists('account.invoice'):
            return 'account.invoice'
        elif self.check_model_exists('account.move'):
            return 'account.move'
        else:
            raise Exception("Neither account.invoice nor account.move model found")
    
    def get_invoices(self, limit=None, offset=0, invoice_model=None):
        """Get customer invoices from Odoo 14"""
        if not invoice_model:
            invoice_model = self._get_invoice_model()
        
        # Determine field names based on model
        if invoice_model == 'account.move':
            # Odoo 15+ or Odoo 14 with account.move field names
            domain = [('move_type', '=', 'out_invoice')]
            fields = [
                'name', 'partner_id', 'invoice_date', 'invoice_date_due', 'state',
                'amount_total', 'amount_untaxed', 'amount_tax', 'currency_id',
                'line_ids', 'invoice_payment_term_id', 'journal_id', 'fiscal_position_id',
                'narration'
            ]
        else:
            # Odoo 14 field names (account.invoice)
            domain = [('type', '=', 'out_invoice')]
            fields = [
                'name', 'partner_id', 'date_invoice', 'date_due', 'state',
                'amount_total', 'amount_untaxed', 'amount_tax', 'currency_id',
                'invoice_line_ids', 'payment_term_id', 'journal_id', 'fiscal_position_id',
                'comment', 'invoice_payment_term_id', 'invoice_date', 'invoice_date_due'
            ]
        return self.search_read(invoice_model, domain, fields=fields, limit=limit, offset=offset)
    
    def get_purchase_invoices(self, limit=None, offset=0, invoice_model=None):
        """Get vendor bills (purchase invoices) from Odoo 14"""
        if not invoice_model:
            invoice_model = self._get_invoice_model()
        
        # Determine field names based on model
        if invoice_model == 'account.move':
            # Odoo 15+ or Odoo 14 with account.move field names
            domain = [('move_type', '=', 'in_invoice')]
            fields = [
                'name', 'partner_id', 'invoice_date', 'invoice_date_due', 'state',
                'amount_total', 'amount_untaxed', 'amount_tax', 'currency_id',
                'line_ids', 'invoice_payment_term_id', 'journal_id', 'fiscal_position_id',
                'narration'
            ]
        else:
            # Odoo 14 field names (account.invoice)
            domain = [('type', '=', 'in_invoice')]
            fields = [
                'name', 'partner_id', 'date_invoice', 'date_due', 'state',
                'amount_total', 'amount_untaxed', 'amount_tax', 'currency_id',
                'invoice_line_ids', 'payment_term_id', 'journal_id', 'fiscal_position_id',
                'comment', 'invoice_payment_term_id', 'invoice_date', 'invoice_date_due'
            ]
        return self.search_read(invoice_model, domain, fields=fields, limit=limit, offset=offset)
    
    def get_invoice_lines(self, invoice_id, invoice_model=None):
        """Get invoice line items for a single invoice"""
        if not invoice_model:
            invoice_model = self._get_invoice_model()
        
        # Determine line model and field name based on invoice model
        if invoice_model == 'account.move':
            line_model = 'account.move.line'
            line_field = 'move_id'
            # Odoo 14's account.move.line doesn't have analytic_distribution
            # Use account_analytic_id instead (Odoo 14 field)
            fields = [
                'product_id', 'name', 'quantity', 'price_unit', 'discount',
                'price_subtotal', 'price_total', 'tax_ids', 'account_id',
                'account_analytic_id', 'sequence', 'display_type'
            ]
        else:
            line_model = 'account.invoice.line'
            line_field = 'invoice_id'
            fields = [
                'product_id', 'name', 'quantity', 'price_unit', 'discount',
                'price_subtotal', 'price_total', 'tax_ids', 'account_id',
                'account_analytic_id', 'sequence'
            ]
        
        try:
            # Filter out section/note lines if display_type exists
            domain = [(line_field, '=', invoice_id)]
            # Only filter by display_type if the model supports it
            # For Odoo 14, we'll try it but catch errors if it doesn't exist
            try:
                if invoice_model == 'account.move':
                    # Check if display_type field exists by trying a search first
                    test_result = self.execute(
                        line_model,
                        'search',
                        [[(line_field, '=', invoice_id), ('display_type', '!=', False)]],
                        {'limit': 1}
                    )
                    if test_result is not None:
                        domain.append(('display_type', 'in', [False, 'product']))
            except:
                # display_type might not exist, skip the filter
                pass
            
            lines = self.search_read(
                line_model,
                domain,
                fields=fields
            )
            return lines
        except Exception as e:
            _logger.error(f"Error getting invoice lines from {line_model}: {str(e)}")
            # If account.move.line fails, try account.invoice.line as fallback
            if invoice_model == 'account.move':
                try:
                    _logger.info("Trying account.invoice.line as fallback...")
                    return self.search_read(
                        'account.invoice.line',
                        [('invoice_id', '=', invoice_id)],
                        fields=[
                            'product_id', 'name', 'quantity', 'price_unit', 'discount',
                            'price_subtotal', 'price_total', 'tax_ids', 'account_id',
                            'account_analytic_id', 'sequence'
                        ]
                    )
                except Exception as e2:
                    _logger.error(f"Fallback to account.invoice.line also failed: {str(e2)}")
                    return []
            return []
    
    def get_invoice_lines_batch(self, invoice_ids, invoice_model=None):
        """Get invoice line items for multiple invoices at once (optimized)"""
        if not invoice_model:
            invoice_model = self._get_invoice_model()
        
        # Determine line model and field name based on invoice model
        if invoice_model == 'account.move':
            line_model = 'account.move.line'
            line_field = 'move_id'
            # Odoo 14's account.move.line doesn't have analytic_distribution
            fields = [
                'product_id', 'name', 'quantity', 'price_unit', 'discount',
                'price_subtotal', 'price_total', 'tax_ids', 'account_id',
                'account_analytic_id', 'sequence', 'display_type', 'move_id'
            ]
        else:
            line_model = 'account.invoice.line'
            line_field = 'invoice_id'
            fields = [
                'product_id', 'name', 'quantity', 'price_unit', 'discount',
                'price_subtotal', 'price_total', 'tax_ids', 'account_id',
                'account_analytic_id', 'sequence', 'invoice_id'
            ]
        
        try:
            domain = [(line_field, 'in', invoice_ids)]
            # Only filter by display_type if it exists (Odoo 14 might not have it)
            try:
                if invoice_model == 'account.move':
                    # Try to check if display_type exists
                    test_result = self.execute(
                        line_model,
                        'search',
                        [[(line_field, 'in', invoice_ids), ('display_type', '!=', False)]],
                        {'limit': 1}
                    )
                    if test_result is not None:
                        domain.append(('display_type', 'in', [False, 'product']))
            except:
                pass
            
            all_lines = self.search_read(
                line_model,
                domain,
                fields=fields,
                limit=10000  # Large limit for batch processing
            )
            
            # Group lines by invoice_id
            lines_by_invoice = {}
            for line in all_lines:
                inv_id = line.get(line_field)
                if isinstance(inv_id, list):
                    inv_id = inv_id[0] if inv_id else None
                if inv_id:
                    if inv_id not in lines_by_invoice:
                        lines_by_invoice[inv_id] = []
                    lines_by_invoice[inv_id].append(line)
            
            return lines_by_invoice
        except Exception as e:
            _logger.error(f"Error getting invoice lines batch from {line_model}: {str(e)}")
            return {}
    
    def get_partner(self, partner_id):
        """Get partner details"""
        fields = [
            'name', 'email', 'phone', 'mobile', 'street', 'street2',
            'city', 'state_id', 'zip', 'country_id', 'vat', 'is_company',
            'customer_rank', 'supplier_rank'
        ]
        records = self.read('res.partner', [partner_id], fields=fields)
        return records[0] if records else None
    
    def get_product(self, product_id):
        """Get product details"""
        fields = [
            'name', 'default_code', 'barcode', 'list_price', 'standard_price',
            'categ_id', 'uom_id', 'type', 'sale_ok', 'purchase_ok',
            'description', 'description_sale', 'description_purchase'
        ]
        records = self.read('product.product', [product_id], fields=fields)
        return records[0] if records else None
    
    def get_currency(self, currency_id):
        """Get currency details"""
        fields = ['name', 'symbol', 'rate']
        records = self.read('res.currency', [currency_id], fields=fields)
        return records[0] if records else None
    
    def get_journal(self, journal_id):
        """Get journal details"""
        fields = ['name', 'code', 'type', 'currency_id']
        records = self.read('account.journal', [journal_id], fields=fields)
        return records[0] if records else None
    
    def get_sale_order_lines(self, sale_order_id):
        """Get order lines for a sale order"""
        try:
            # Get order line IDs from the sale order
            order_data = self.read('sale.order', [sale_order_id], ['order_line'])
            if not order_data:
                return []
            
            order_line_ids = order_data[0].get('order_line', [])
            if not order_line_ids:
                return []
            
            # Extract IDs
            line_ids = []
            for line_id in order_line_ids:
                if isinstance(line_id, int):
                    line_ids.append(line_id)
                elif isinstance(line_id, (list, tuple)) and len(line_id) > 0:
                    line_ids.append(line_id[0])
            
            if not line_ids:
                return []
            
            # Read order lines
            return self.read('sale.order.line', line_ids, [
                'product_id', 'name', 'product_uom_qty', 'product_uom', 
                'price_unit', 'discount', 'price_subtotal', 'tax_id', 
                'sequence', 'display_type'
            ])
        except Exception as e:
            _logger.error("Error getting sale order lines for order %s: %s" % (sale_order_id, str(e)))
            return []
    
    # REST API Methods (new approach - Odoo 14 provides data via REST API)
    def get_count_rest(self, model):
        """Get count of records using REST API"""
        try:
            url = '%s/api/odoo19/count' % self.url
            params = {'model': model}
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get('success'):
                return data.get('count', 0)
            else:
                _logger.error("Error getting count: %s" % data.get('error'))
                return 0
        except Exception as e:
            _logger.error("Error in get_count_rest: %s" % str(e))
            return 0
    
    def get_customers_rest(self, limit=None, offset=0):
        """Get customers using REST API"""
        try:
            url = '%s/api/odoo19/customers' % self.url
            params = {}
            if limit:
                params['limit'] = limit
            if offset:
                params['offset'] = offset
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get('success'):
                return data.get('data', [])
            else:
                _logger.error("Error getting customers: %s" % data.get('error'))
                return []
        except Exception as e:
            _logger.error("Error in get_customers_rest: %s" % str(e))
            return []
    
    def get_vendors_rest(self, limit=None, offset=0):
        """Get vendors using REST API"""
        try:
            url = '%s/api/odoo19/vendors' % self.url
            params = {}
            if limit:
                params['limit'] = limit
            if offset:
                params['offset'] = offset
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get('success'):
                return data.get('data', [])
            else:
                _logger.error("Error getting vendors: %s" % data.get('error'))
                return []
        except Exception as e:
            _logger.error("Error in get_vendors_rest: %s" % str(e))
            return []
    
    def get_products_rest(self, limit=None, offset=0):
        """Get products using REST API"""
        try:
            url = '%s/api/odoo19/products' % self.url
            params = {}
            if limit:
                params['limit'] = limit
            if offset:
                params['offset'] = offset
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get('success'):
                return data.get('data', [])
            else:
                _logger.error("Error getting products: %s" % data.get('error'))
                return []
        except Exception as e:
            _logger.error("Error in get_products_rest: %s" % str(e))
            return []
    
    def get_invoices_rest(self, limit=None, offset=0, date_from=None, date_to=None):
        """Get invoices using REST API"""
        try:
            url = '%s/api/odoo19/invoices' % self.url
            params = {}
            if limit:
                params['limit'] = limit
            if offset:
                params['offset'] = offset
            if date_from:
                params['date_from'] = date_from
            if date_to:
                params['date_to'] = date_to
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get('success'):
                return data.get('data', [])
            else:
                _logger.error("Error getting invoices: %s" % data.get('error'))
                return []
        except Exception as e:
            _logger.error("Error in get_invoices_rest: %s" % str(e))
            return []
    
    def get_purchase_invoices_rest(self, limit=None, offset=0, date_from=None, date_to=None):
        """Get purchase invoices using REST API"""
        try:
            url = '%s/api/odoo19/purchase_invoices' % self.url
            params = {}
            if limit:
                params['limit'] = limit
            if offset:
                params['offset'] = offset
            if date_from:
                params['date_from'] = date_from
            if date_to:
                params['date_to'] = date_to
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get('success'):
                return data.get('data', [])
            else:
                _logger.error("Error getting purchase invoices: %s" % data.get('error'))
                return []
        except Exception as e:
            _logger.error("Error in get_purchase_invoices_rest: %s" % str(e))
            return []
    
    def get_quotations_rest(self, limit=None, offset=0):
        """Get quotations using REST API"""
        try:
            url = '%s/api/odoo19/quotations' % self.url
            params = {}
            if limit:
                params['limit'] = limit
            if offset:
                params['offset'] = offset
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get('success'):
                return data.get('data', [])
            else:
                _logger.error("Error getting quotations: %s" % data.get('error'))
                return []
        except Exception as e:
            _logger.error("Error in get_quotations_rest: %s" % str(e))
            return []
    
    def get_sales_orders_rest(self, limit=None, offset=0):
        """Get sales orders using REST API"""
        try:
            url = '%s/api/odoo19/sales_orders' % self.url
            params = {}
            if limit:
                params['limit'] = limit
            if offset:
                params['offset'] = offset
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get('success'):
                return data.get('data', [])
            else:
                _logger.error("Error getting sales orders: %s" % data.get('error'))
                return []
        except Exception as e:
            _logger.error("Error in get_sales_orders_rest: %s" % str(e))
            return []
    

