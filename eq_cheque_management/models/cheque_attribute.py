# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ChequeAttribute(models.Model):
    _name = 'cheque.attribute'
    _description = "Cheque Attributes"
    _check_company_auto = True

    # Selection field for predefined cheque attributes
    attribute_name = fields.Selection([
        ('cheque_date', 'Cheque Date'),
        ('pay_to', 'Pay To'),
        ('amount_words1', 'Amount In Words Line1'),
        ('amount_words2', 'Amount In Words Line2'),
        ('amount_box', 'Amount Box'),
        ('account_number', 'Account Number'),
        ('a_c_label', 'A/C Label')
    ], string="Attribute Name", required=True)

    name = fields.Char(string="Attribute")

    # Styling fields for cheque attributes
    font_size = fields.Integer(string="Font Size", default=20)
    letter_space = fields.Integer(string="Letter Space", default=0)
    top_displacement = fields.Float(string="Top Displacement", default=0.0)
    left_displacement = fields.Float(string="Left Displacement", default=0.0)
    height = fields.Float(string="Height", default=0.0)
    width = fields.Float(string="Width", default=0.0)

    cheque_id = fields.Many2one("bank.cheque", string="Cheque", ondelete="cascade", required=True, check_company=True)
    background_image = fields.Binary("Cheque Background Image")

    bank_cheque_id = fields.Many2one("bank.cheque", string="Cheque Attributes")

    # Fields for dynamic positioning (Bounding Box)
    x1 = fields.Integer("X1")
    y1 = fields.Integer("Y1")
    x2 = fields.Integer("X2")
    y2 = fields.Integer("Y2")
    
    company_id = fields.Many2one('res.company', string='Company', related='cheque_id.company_id', store=True, readonly=True)

    @api.model
    def update_coordinates(self, attribute_id, x1, y1, x2, y2):
        """Update the coordinates of the attribute"""
        record = self.browse(attribute_id)
        if record:
            record.write({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2})
            return {"status": "success"}
        return {"status": "error"}

