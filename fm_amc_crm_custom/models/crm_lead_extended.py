# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Lead number field - unique identifier
    lead_number = fields.Char(string='Lead Number', 
                             help='Unique lead number for this opportunity',
                             copy=False)
    
    # Sales agent field
    sales_agent = fields.Char(string='Sales Agent', 
                             help='Sales agent for this opportunity')
    
    _sql_constraints = [
        ('lead_number_unique', 'UNIQUE(lead_number)', 'Lead Number must be unique!')
    ]

