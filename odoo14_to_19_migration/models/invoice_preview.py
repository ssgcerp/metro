# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import json

_logger = logging.getLogger(__name__)


class InvoicePreview(models.TransientModel):
    _name = 'odoo14.invoice.preview'
    _description = 'Odoo 14 Invoice Preview'
    _order = 'invoice_date desc, name'

    name = fields.Char(string='Invoice Number', readonly=True)
    partner_name = fields.Char(string='Partner', readonly=True)
    partner_address = fields.Text(string='Partner Address', readonly=True)
    invoice_date = fields.Date(string='Invoice Date', readonly=True)
    date_due = fields.Date(string='Due Date', readonly=True)
    amount_total = fields.Float(string='Total Amount', readonly=True)
    amount_untaxed = fields.Float(string='Untaxed Amount', readonly=True)
    amount_tax = fields.Float(string='Tax Amount', readonly=True)
    state = fields.Char(string='State', readonly=True)
    invoice_type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
    ], string='Type', readonly=True)
    currency_name = fields.Char(string='Currency', readonly=True)
    journal_name = fields.Char(string='Journal', readonly=True)
    comment = fields.Text(string='Comment/Narration', readonly=True)
    invoice_line_data = fields.Text(string='Invoice Lines Data', readonly=True)
    invoice_data_json = fields.Text(string='Full Invoice Data (JSON)', readonly=True)
    invoice_line_ids = fields.One2many('odoo14.invoice.line.preview', 'invoice_preview_id', string='Invoice Lines', readonly=True)
    
    def action_previous(self):
        """Navigate to previous invoice"""
        self.ensure_one()
        prev_invoice = self.search([
            ('id', '<', self.id)
        ], order='id desc', limit=1)
        
        if not prev_invoice:
            raise UserError('This is the first invoice.')
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice Preview',
            'res_model': 'odoo14.invoice.preview',
            'view_mode': 'form',
            'target': 'new',
            'res_id': prev_invoice.id,
        }
    
    def action_next(self):
        """Navigate to next invoice"""
        self.ensure_one()
        next_invoice = self.search([
            ('id', '>', self.id)
        ], order='id asc', limit=1)
        
        if not next_invoice:
            raise UserError('This is the last invoice.')
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice Preview',
            'res_model': 'odoo14.invoice.preview',
            'view_mode': 'form',
            'target': 'new',
            'res_id': next_invoice.id,
        }
    
    def _get_invoice_lines_display(self):
        """Get formatted invoice lines for display"""
        if not self.invoice_line_data:
            return []
        try:
            return json.loads(self.invoice_line_data)
        except:
            return []

