# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import json


class DashboardController(http.Controller):

    @http.route('/project/dashboard/<int:project_id>', type='jsonrpc', auth='user', methods=['POST'], csrf=False)
    def get_dashboard_data(self, project_id, **kwargs):
        """
        Controller route to get dashboard data for a project.
        
        :param project_id: ID of the project
        :return: JSON response with dashboard values
        """
        try:
            helper = request.env['project.dashboard.helper']
            values = helper.get_project_dashboard_values(project_id)
            return {
                'status': 'success',
                'data': values
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

