# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AMCContractAsset(models.Model):
    _name = 'amc.contract.asset'
    _description = 'AMC Contract Asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'code'

    name = fields.Char(string='Asset Name', required=True, tracking=True)
    code = fields.Char(string='Asset Code', readonly=True, default='New', copy=False, tracking=True)
    contract_id = fields.Many2one('amc.contract', string='Contract', required=True, ondelete='cascade', tracking=True)
    
    category = fields.Char(string='Category', tracking=True)
    location = fields.Char(string='Location', tracking=True)
    serial_number = fields.Char(string='Serial Number', tracking=True)
    model_number = fields.Char(string='Model Number', tracking=True)
    brand = fields.Char(string='Brand/Make', tracking=True)
    
    date_installation = fields.Date(string='Installation Date', tracking=True)
    warranty_expiry = fields.Date(string='Warranty Expiry', tracking=True)
    
    notes = fields.Text(string='Notes')
    active = fields.Boolean(string='Active', default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('amc.contract.asset') or 'New'
        return super(AMCContractAsset, self).create(vals_list)
