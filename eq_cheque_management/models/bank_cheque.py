# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class BankCheque(models.Model):
    _name = 'bank.cheque'
    _description = "Bank Cheque Configuration"
    _check_company_auto = True

    name = fields.Char(string="Name", required=True, help="Name of the bank cheque configuration")
    bank_identifier_code = fields.Char(string="Bank Identifier Code", help="BIC/SWIFT code")
    bank_address = fields.Text(string="Bank Address")
    phone = fields.Char(string="Phone Number")
    email = fields.Char(string="Email")
    font_size = fields.Float(string="Font Size", default=20, help="Default font size for cheque printing")
    cheque_image = fields.Binary(string="Cheque Image", required=True, attachment=True, help="Background image of the cheque")
    cheque_no_lm = fields.Float(string="Cheque No Left Margin", help="Left margin for cheque number")
    cheque_no_tm = fields.Float(string="Cheque No Top Margin", help="Top margin for cheque number")
    amount_word_lm = fields.Float(string="Amount in Words Left Margin", help="Left margin for amount in words")
    amount_word_tm = fields.Float(string="Amount in Words Top Margin", help="Top margin for amount in words")

    measurement_unit = fields.Selection([
        ('mm', 'MM'),
        ('cm', 'CM'),
        ('in', 'Inches')
    ], string="Measurement Unit", default='mm', required=True)

    cheque_height = fields.Float(string="Cheque Height", help="Height of the cheque")
    cheque_width = fields.Float(string="Cheque Width", help="Width of the cheque")
    maximum_characters = fields.Integer(string="Maximum Characters", help="Maximum characters per line")

    cheque_attribute_ids = fields.One2many("cheque.attribute", "cheque_id", string="Cheque Attributes", help="Configuration for cheque field positioning")
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True, ondelete='cascade')
    company_ids = fields.Many2many('res.company', 'bank_cheque_company_rel', 'bank_cheque_id', 'company_id', string='Allowed Companies', help="Companies that can access this bank cheque configuration")
    
    report_preview = fields.Html("Live Cheque Preview", compute="_compute_preview_fields", store=True)
    cheque_background = fields.Binary("Cheque Background Image", compute="_compute_preview_fields", store=False)

    @api.constrains('phone')
    def _check_phone_number_numeric(self):
        """Validate phone number contains only digits"""
        for record in self:
            if record.phone and not record.phone.replace('+', '').replace('-', '').replace(' ', '').isdigit():
                raise ValidationError("Phone number must contain only digits, spaces, hyphens, and plus sign.")

    @api.depends('cheque_image', 'font_size')
    def _compute_preview_fields(self):
        """Compute preview fields for cheque"""
        for record in self:
            record.cheque_background = record.cheque_image
            # Preview will be rendered in the view template if needed
            record.report_preview = False

    @api.model
    def default_get(self, fields_list):
        """Set default cheque attributes when creating a new bank cheque"""
        res = super().default_get(fields_list)
        
        default_lines = []
        attributes = [
            ('cheque_date', 'Cheque Date'),
            ('pay_to', 'Pay To'),
            ('amount_words1', 'Amount In Words Line1'),
            ('amount_words2', 'Amount In Words Line2'),
            ('amount_box', 'Amount Box'),
            ('account_number', 'Account Number'),
            ('a_c_label', 'A/C Label')
        ]

        for attr_name, _ in attributes:
            default_lines.append((0, 0, {
                'attribute_name': attr_name,
                'x1': 0,
                'x2': 0,
                'y1': 0,
                'y2': 0,
                'top_displacement': 0.0,
                'left_displacement': 0.0,
                'width': 0.0,
                'height': 0.0,
                'letter_space': 0,
            }))

        res['cheque_attribute_ids'] = default_lines
        return res
