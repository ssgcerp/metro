# -*- coding: utf-8 -*-

# Import controllers - this makes them register with Odoo
try:
    from . import migration_cron_controller
    from . import test_route
    from . import minimal_test
    import logging
    _logger = logging.getLogger(__name__)
    _logger.info("=" * 50)
    _logger.info("CONTROLLERS __init__.py: All controllers imported successfully!")
    _logger.info("=" * 50)
except Exception as e:
    import logging
    _logger = logging.getLogger(__name__)
    _logger.error("=" * 50)
    _logger.error("CONTROLLERS __init__.py: ERROR importing controllers!")
    _logger.error("Error: %s", str(e))
    _logger.error("=" * 50)
    raise
