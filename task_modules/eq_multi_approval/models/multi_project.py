from odoo import models, api,fields
import logging

_logger = logging.getLogger(__name__)

class MultiProjectProject(models.Model):
    _inherit = 'project.project'

    @api.model
    def _get_domain_for_user(self):
        user = self.env.user
        domain = [
            '|', '|', '|', '|',
            ('project_admin', '=', user.id),
            ('project_manager', '=', user.id),
            ('technical_manager', '=', user.id),
            ('purchase_officer', '=', user.id),
            ('engineer', '=', user.id)
        ]
        return domain

    @api.model
    def _apply_project_project_rule(self, operation, domain=None):
        if operation == 'read':
            if domain is None:
                domain = []
            user_domain = self._get_domain_for_user()
            domain += user_domain
        return super(MultiProjectProject, self)._apply_project_project_rule(operation, domain)