# -*- coding: utf-8 -*-
# Simple test route to verify controller loading works

from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class TestRouteController(http.Controller):
    """Test controller to verify routes work"""

    @http.route('/migration/test', type='http', auth='public', methods=['GET'], csrf=False)
    def test_route(self, **kwargs):
        """Simple test route that should always work"""
        _logger.info("TEST ROUTE CALLED - Controller is working!")
        return request.make_response(
            'OK - Controller is loaded and working!\n',
            headers=[('Content-Type', 'text/plain; charset=utf-8')]
        )

