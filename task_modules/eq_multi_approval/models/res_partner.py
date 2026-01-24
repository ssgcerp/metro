# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import api, fields, models, _

class ResPartner(models.Model):
    _inherit = 'res.partner'
    _description = 'Res Partner'

    vend_cus_id = fields.Char(string='Unique ID', required=True)

   