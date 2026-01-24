from odoo import models, fields

class ProjectType(models.Model):
    _name = 'project.type'
    _description = 'Project Type'

    name = fields.Char(string='Name', required=True)
    use_gmb = fields.Boolean(string="Enable GMB")
    use_social = fields.Boolean(string="Enable Social Accounts")
