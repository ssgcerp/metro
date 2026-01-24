# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleQuotationStage(models.Model):
    _name = 'sale.quotation.stage'
    _description = 'Sale Quotation Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10, help='Order of stages')
    code = fields.Char(string='Code', required=True, help='Stage code for programmatic reference')
    fold = fields.Boolean(string='Folded', help='Folded in kanban view')
    
    # Stage behavior flags
    is_draft_stage = fields.Boolean(string='Is Draft Stage', help='This stage represents draft quotations')
    is_locked_stage = fields.Boolean(string='Is Locked Stage', help='Quotations in this stage cannot be modified')
    is_cancelled_stage = fields.Boolean(string='Is Cancelled Stage', help='This stage represents cancelled quotations')
    is_confirmed_stage = fields.Boolean(string='Is Confirmed Stage', help='This stage represents confirmed quotations (Sales Orders)')
    
    # Visual customization
    color = fields.Integer(string='Color', default=0, help='Color code for this stage')

