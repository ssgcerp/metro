# -*- coding: utf-8 -*-
# Minimal test controller to verify basic controller loading

from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

_logger.info("=" * 50)
_logger.info("MINIMAL_TEST_CONTROLLER: Loading...")
_logger.info("=" * 50)


class MinimalTestController(http.Controller):
    """Minimal test controller"""

    @http.route('/migration/minimal_test', type='http', auth='public', methods=['GET'], csrf=False)
    def minimal_test_public(self, **kwargs):
        """Test route with auth='public'"""
        _logger.info("MINIMAL_TEST: public route called!")
        return request.make_response(
            'OK - Minimal test controller with auth=public works!\n',
            headers=[('Content-Type', 'text/plain; charset=utf-8')]
        )

    @http.route('/migration/minimal_test_user', type='http', auth='user', methods=['GET'], csrf=False)
    def minimal_test_user(self, **kwargs):
        """Test route with auth='user'"""
        _logger.info("MINIMAL_TEST: user route called!")
        return request.make_response(
            'OK - Minimal test controller with auth=user works!\n',
            headers=[('Content-Type', 'text/plain; charset=utf-8')]
        )

