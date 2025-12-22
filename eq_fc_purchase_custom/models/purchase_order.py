# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Header Fields
    attention = fields.Char(string="Attention", help="Attention person name")
    delivery_address = fields.Char(string="Delivery Address", help="Delivery address for the purchase order")
    attention_mobile_number = fields.Char(string="Attention Mobile Number", help="Mobile number of attention person")
    is_with_stamp = fields.Boolean(string="With Stamp", default=False, help="Include stamp on documents")
    is_wo_header = fields.Boolean(string="Invoice Without Header", default=False, help="Invoice without header")
    is_lumpsum = fields.Boolean(string="Lumpsum", default=False, help="Lumpsum order")
    attention_note = fields.Text(string="Attention Note", help="Additional notes for attention")
    ask_confirmation = fields.Boolean(string="Ask confirmation", default=False, help="Ask for confirmation")
    
    # Receipt and Delivery
    receipt_date = fields.Datetime(string="Receipt Date", help="Expected receipt date")
    deliver_to = fields.Many2one('stock.location', string="Deliver To", help="Delivery location")
    
    # Other Information Fields
    verified_by = fields.Char(string='Verified by', readonly=True, help="Person who verified the order")
    approved_by = fields.Char(string='Approved by', readonly=True, help="Person who approved the order")
    project_code = fields.Many2one('project.project', string='Project Code', help="Related project")
    project = fields.Char(string='Project Name', compute='_compute_project_name', store=True, help="Project name")
    order_contact = fields.Char(string='Order Contact', help="Contact person for the order")
    contact_no = fields.Char(string='Contact no', help="Contact number")
    supplier_quote_ref = fields.Char(string='Supplier Quote Ref', help="Supplier quotation reference")
    internal_notes = fields.Text(string='Remarks', help="Internal remarks and notes")
    
    # Computed Fields
    sale_order_reference = fields.Char(string="Sale Order Reference", compute='_compute_sale_order_reference', store=False, help="Related sale order references")
    billing_status = fields.Selection([
        ('nothing_to_bill', 'Nothing to Bill'),
        ('to_bill', 'To Bill'),
        ('billed', 'Billed'),
    ], string='Billing Status', compute='_compute_billing_status', store=False, help="Current billing status")
    
    # Project Request Lines (for Projects tab)
    project_request_line_ids = fields.One2many('purchase.project.request.line', 'purchase_order_id', string="Project Request Lines")
    
    # Delivery Order Lines (for DO Details tab)
    delivery_order_line_ids = fields.One2many('purchase.delivery.order.line', 'purchase_order_id', string="Delivery Order Lines")
    
    @api.depends('project_code')
    def _compute_project_name(self):
        """Compute project name from project_code"""
        for rec in self:
            rec.project = rec.project_code.name if rec.project_code else False
    
    @api.depends('project_code', 'project_request_line_ids')
    def _compute_sale_order_reference(self):
        """Compute sale order reference from project"""
        for record in self:
            sale_orders = []
            if record.project_code:
                sale_orders = self.env['sale.order'].search([('project_id', '=', record.project_code.id)])
                order_names = ','.join(sale_orders.mapped('name'))
                record.sale_order_reference = order_names if order_names else False
            elif record.project_request_line_ids:
                # Get unique sale orders from project request lines
                projects = record.project_request_line_ids.filtered(lambda r: r.requested_project_id).mapped('requested_project_id')
                for project in projects:
                    project_sale_orders = self.env['sale.order'].search([('project_id', '=', project.id)])
                    for so in project_sale_orders:
                        if so.name not in sale_orders:
                            sale_orders.append(so.name)
                record.sale_order_reference = ','.join(sale_orders) if sale_orders else False
            else:
                record.sale_order_reference = False
    
    def _compute_billing_status(self):
        """Compute billing status based on invoice state"""
        for order in self:
            # invoice_status field exists in purchase.order model
            invoice_status = getattr(order, 'invoice_status', 'no')
            if invoice_status == 'no':
                order.billing_status = 'nothing_to_bill'
            elif invoice_status == 'to invoice':
                order.billing_status = 'to_bill'
            elif invoice_status == 'invoiced':
                order.billing_status = 'billed'
            else:
                order.billing_status = 'nothing_to_bill'
    
    @api.onchange('partner_id')
    def _onchange_partner_id_custom(self):
        """Set attention and attention mobile number from partner"""
        if self.partner_id:
            # Try to get attention person from partner if available
            if hasattr(self.partner_id, 'attention_person_id') and self.partner_id.attention_person_id:
                self.attention = self.partner_id.attention_person_id.name
                self.attention_mobile_number = self.partner_id.attention_person_id.mobile
            else:
                # Fallback: try to get from partner contact
                contact = self.partner_id.child_ids.filtered(lambda c: c.type == 'contact')[:1]
                if contact:
                    self.attention = contact.name
                    self.attention_mobile_number = contact.mobile or contact.phone
    
    @api.onchange('project_code')
    def _onchange_project_code(self):
        """Set project name and update order lines"""
        if self.project_code:
            self.project = self.project_code.name
            # Update order lines with project if not set
            for line in self.order_line:
                if not line.project_id:
                    line.project_id = self.project_code.id
                    if self.project_code.partner_id:
                        line.customer_id = self.project_code.partner_id.id
        else:
            self.project = False
    
    def action_approve_quotation(self):
        """Approve quotation and set approved_by"""
        self.write({
            'approved_by': self.env.user.name,
        })
        return super().button_approve() if hasattr(super(), 'button_approve') else True
    
    def button_confirm(self):
        """Override to set verified_by on confirmation"""
        result = super().button_confirm()
        if not self.verified_by:
            self.verified_by = self.env.user.name
        return result


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    brand_id = fields.Many2one('product.brand', string='Brand', help="Product brand")
    project_id = fields.Many2one('project.project', string="Project", help="Related project")
    customer_id = fields.Many2one('res.partner', string="Customer", help="Customer for this line")
    # Note: project.project.orderline model doesn't exist in Odoo 19, so this field is removed
    # project_orderline_id = fields.Many2one('project.project.orderline', string="Project Orderline", help="Related project order line", ondelete='set null')
    
    @api.onchange('product_id')
    def _onchange_product_id_custom(self):
        """Set brand_id when product changes"""
        res = super()._onchange_product_id() if hasattr(super(), '_onchange_product_id') else {}
        if self.product_id and hasattr(self.product_id, 'brand_id') and self.product_id.brand_id:
            # Check if product.brand model exists
            if 'product.brand' in self.env:
                self.brand_id = self.product_id.brand_id.id
        return res
    
    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        """Filter products by brand"""
        if self.brand_id and not self.product_id:
            # Check if product.brand model exists and product has brand_id field
            if 'product.brand' in self.env and hasattr(self.env['product.product'], 'brand_id'):
                return {'domain': {'product_id': [('brand_id', '=', self.brand_id.id)]}}
        return {}


class PurchaseProjectRequestLine(models.Model):
    _name = 'purchase.project.request.line'
    _description = 'Purchase Project Request Line'
    _order = 'order_date desc, id desc'

    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order", required=True, ondelete='cascade', index=True)
    order_date = fields.Date(string='Order Date', required=True, default=lambda self: fields.Date.today())
    requested_project_id = fields.Many2one('project.project', string="Requested Project", required=True)
    requested_product = fields.Char(string="Requested Product", required=True)
    requested_qty = fields.Float(string="Requested Qty", required=True, default=1.0)
    requested_user = fields.Char(string="Requested User", help="User who requested this product")


class PurchaseDeliveryOrderLine(models.Model):
    _name = 'purchase.delivery.order.line'
    _description = 'Purchase Delivery Order Line'
    _order = 'order_date desc, id desc'

    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order", required=True, ondelete='cascade', index=True)
    order_date = fields.Date(string='Order Date', required=True, default=lambda self: fields.Date.today())
    delivery_number = fields.Char(string="Delivery Number", required=True, help="Delivery order number")

