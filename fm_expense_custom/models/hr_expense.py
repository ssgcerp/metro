from odoo import models, fields

class HrExpense(models.Model):
    _inherit = 'hr.expense'

    x_reference_no = fields.Char(string='Reference number')
    project_id = fields.Many2one('project.project', string='Project', domain="[('company_id', '=', company_id)]")
