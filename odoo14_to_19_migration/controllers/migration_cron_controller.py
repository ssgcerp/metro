# -*- coding: utf-8 -*-

import logging
import os
from datetime import datetime
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


def _log_failed_system_type_migration(system_type_name, error_detail):
    """Log failed system type migration to a file for later processing"""
    try:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'failed_system_type_migrations.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {system_type_name} | {error_detail[:200]}\n")
        
        _logger.info("Failed system type migration logged to: %s", log_file)
    except Exception as e:
        _logger.warning("Could not write to failed system type migrations log: %s", str(e))


def _log_failed_migration(quotation_number, error_detail):
    """Log failed migration to a file for later processing"""
    try:
        # Get log directory (use Odoo log directory or create one)
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'failed_migrations.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {quotation_number} | {error_detail[:200]}\n")
        
        _logger.info("Failed migration logged to: %s", log_file)
    except Exception as e:
        _logger.warning("Could not write to failed migrations log: %s", str(e))


def _log_failed_rfq_migration(rfq_number, error_detail):
    """Log failed RFQ migration to a file for later processing"""
    try:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'failed_rfq_migrations.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {rfq_number} | {error_detail[:200]}\n")
        
        _logger.info("Failed RFQ migration logged to: %s", log_file)
    except Exception as e:
        _logger.warning("Could not write to failed RFQ migrations log: %s", str(e))

# Log when controller is loaded
_logger.info("=" * 50)
_logger.info("MigrationCronController: Module loading...")
_logger.info("=" * 50)


class MigrationCronController(http.Controller):
    """Simple HTTP endpoint for cron-like migration processing"""

    # Log when class is defined
    _logger.info("MigrationCronController: Class definition loaded")

    @http.route('/migration/process_one', type='http', auth='public', methods=['GET'], csrf=False)
    def process_one_quotation(self, **kwargs):
        """
        Process one quotation from the queue.
        Can be called repeatedly like a cron job.
        
        Returns simple text response with status.
        
        Usage: /migration/process_one?db=your_database_name
        """
        _logger.info("=" * 50)
        _logger.info("process_one_quotation ROUTE CALLED!")
        _logger.info("URL: %s", request.httprequest.url if hasattr(request, 'httprequest') and request.httprequest else 'N/A')
        _logger.info("kwargs: %s", kwargs)
        _logger.info("=" * 50)
        try:
            # Get database from query parameter
            # In Odoo, query string parameters are passed as kwargs
            db = kwargs.get('db')
            
            # Fallback: parse from URL if not in kwargs
            if not db and hasattr(request, 'httprequest') and request.httprequest:
                from urllib.parse import parse_qs, urlparse
                try:
                    parsed = urlparse(request.httprequest.url)
                    query_params = parse_qs(parsed.query)
                    if 'db' in query_params:
                        db = query_params['db'][0]
                except:
                    pass
            
            if not db:
                return request.make_response(
                    'ERROR: Database not specified. Use: /migration/process_one?db=your_database_name\n',
                    headers=[('Content-Type', 'text/plain; charset=utf-8')]
                )
            
            # Create environment with specified database
            from odoo.api import Environment
            from odoo import sql_db
            try:
                # Get database connection
                db_conn = sql_db.db_connect(db)
                cr = db_conn.cursor()
            except Exception as reg_error:
                return request.make_response(
                    f'ERROR: Database "{db}" not found: {str(reg_error)}\n',
                    headers=[('Content-Type', 'text/plain; charset=utf-8')]
                )
            
            try:
                env = Environment(cr, 1, {})  # Use user 1 (admin)
                
                # Get migration quotation model
                MigrationQuotation = env['eq.migration.quotation']
            
                # Count total queued - ONLY count 'queued' status from eq.migration.quotation table
                # Use search_count with explicit domain to ensure accuracy
                total_queued = env['eq.migration.quotation'].search_count([
                    ('status', '=', 'queued')
                ])
                _logger.info("Total queued count: %s (status='queued')", total_queued)
                
                # Check for stuck migrations (migrating for more than 10 seconds - very aggressive)
                from datetime import timedelta
                stuck_threshold = fields.Datetime.now() - timedelta(seconds=10)
                
                # Find ALL migrating records
                all_migrating = MigrationQuotation.search([
                    ('status', '=', 'migrating')
                ])
                
                # Reset ALL stuck migrations back to error (don't retry them automatically)
                stuck_count = 0
                for migrating_record in all_migrating:
                    # Check if write_date is older than threshold
                    if migrating_record.write_date and migrating_record.write_date < stuck_threshold:
                        stuck_seconds = int((fields.Datetime.now() - migrating_record.write_date).total_seconds())
                        _logger.warning("Found stuck migration: %s (stuck for %s seconds), resetting to error", 
                                      migrating_record.uploaded_quotation_number,
                                      stuck_seconds)
                        migrating_record.write({
                            'status': 'error',
                            'status_message': 'Migration stuck - reset to error',
                            'error_message': f'Migration was stuck in migrating status for {stuck_seconds} seconds. Last update: {migrating_record.write_date}',
                        })
                        stuck_count += 1
                
                if stuck_count > 0:
                    cr.commit()
                    _logger.warning("Reset %s stuck migration(s) to error status", stuck_count)
                
                # Find currently migrating (recent ones, not stuck - within last 10 seconds)
                currently_migrating = MigrationQuotation.search([
                    ('status', '=', 'migrating'),
                    ('write_date', '>=', stuck_threshold)
                ], limit=1, order='write_date desc')
                
                migrating_quotation = 'None'
                
                # If nothing is migrating, get the first queued one and process it SYNCHRONOUSLY
                quotation_to_process = None
                if not currently_migrating:
                    quotation_to_process = MigrationQuotation.search([
                        ('status', '=', 'queued')
                    ], limit=1, order='id asc')
                
                # Process one quotation SYNCHRONOUSLY if available and nothing is migrating
                if quotation_to_process and not currently_migrating:
                    try:
                        # Only process 'queued' status quotations
                        if quotation_to_process.status != 'queued':
                            migrating_quotation = f"Skipped: {quotation_to_process.status} (not queued)"
                        else:
                            quotation_number = quotation_to_process.uploaded_quotation_number
                            _logger.info("🔄 Starting SYNCHRONOUS migration for quotation %s", quotation_number)
                            
                            # action_migrate requires status='pending_migration', so set it first
                            quotation_to_process.write({
                                'status': 'pending_migration',
                                'status_message': 'Starting migration...',
                            })
                            cr.commit()
                            migrating_quotation = quotation_number
                            
                            # Call action_migrate directly (synchronous) - it will set status to 'migrating' internally
                            try:
                                # Check if quotation already exists in Odoo 19 BEFORE calling action_migrate
                                existing_quotation = env['sale.order'].search([
                                    ('name', '=', quotation_number)
                                ], limit=1)
                                
                                if existing_quotation:
                                    # Quotation already exists - update status to migrated if still queued
                                    if quotation_to_process.status in ('queued', 'pending_migration'):
                                        _logger.info("Quotation %s already exists in Odoo 19 (ID: %s), updating status to migrated", 
                                                   quotation_number, existing_quotation.id)
                                        quotation_to_process.write({
                                            'status': 'migrated',
                                            'status_message': 'Already migrated (existed in system)',
                                            'odoo19_quotation_id': existing_quotation.id,
                                            'in_system_quotation_number': existing_quotation.name,
                                            'migration_date': fields.Datetime.now(),
                                            'error_message': False,
                                        })
                                        cr.commit()
                                        migrating_quotation = f"{quotation_number} - DONE (already existed)"
                                        _logger.info("✅ Quotation %s marked as migrated (already existed)", quotation_number)
                                    else:
                                        migrating_quotation = f"{quotation_number} - Already migrated"
                                        _logger.info("Quotation %s already migrated (status: %s)", quotation_number, quotation_to_process.status)
                                else:
                                    # Quotation doesn't exist - proceed with migration
                                    try:
                                        result = quotation_to_process.action_migrate()
                                        cr.commit()
                                    except Exception as migrate_exception:
                                        # Even if action_migrate raises an exception, check if quotation was actually created
                                        error_msg = str(migrate_exception)
                                        _logger.warning("action_migrate raised exception for %s: %s - checking if quotation was created", 
                                                      quotation_number, error_msg[:100])
                                        
                                        # Check if quotation was actually created despite the exception
                                        created_quotation = env['sale.order'].search([
                                            ('name', '=', quotation_number)
                                        ], limit=1)
                                        
                                        if created_quotation:
                                            # Quotation was created successfully! Update status to migrated
                                            _logger.info("Quotation %s was created successfully despite exception, updating status to migrated", quotation_number)
                                            quotation_to_process.write({
                                                'status': 'migrated',
                                                'status_message': 'Successfully migrated (created despite exception)',
                                                'odoo19_quotation_id': created_quotation.id,
                                                'in_system_quotation_number': created_quotation.name,
                                                'migration_date': fields.Datetime.now(),
                                                'error_message': False,
                                            })
                                            cr.commit()
                                            migrating_quotation = f"{quotation_number} - DONE"
                                            _logger.info("✅ Quotation %s marked as migrated (was created successfully)", quotation_number)
                                        else:
                                            # Quotation was NOT created - this is a real error
                                            _logger.error("Quotation %s was NOT created: %s", quotation_number, error_msg)
                                            raise  # Re-raise the exception to be handled by outer exception handler
                                
                                # Force refresh from database to get actual status
                                quotation_to_process.invalidate_recordset(['status', 'error_message', 'status_message'])
                                # Re-browse to get fresh data from database
                                quotation_to_process = env['eq.migration.quotation'].browse(quotation_to_process.id)
                                
                                # Re-count queued after processing
                                total_queued = env['eq.migration.quotation'].search_count([
                                    ('status', '=', 'queued')
                                ])
                                _logger.info("After migration, queued count: %s", total_queued)
                                
                                # Double-check: If status is error but quotation exists, fix it
                                if quotation_to_process.status == 'error':
                                    # Check if quotation actually exists in Odoo 19
                                    verify_quotation = env['sale.order'].search([
                                        ('name', '=', quotation_number)
                                    ], limit=1)
                                    
                                    if verify_quotation:
                                        # Quotation exists! Update status to migrated
                                        _logger.info("Quotation %s exists in Odoo 19 but status is 'error', fixing to 'migrated'", quotation_number)
                                        quotation_to_process.write({
                                            'status': 'migrated',
                                            'status_message': 'Successfully migrated (verified)',
                                            'odoo19_quotation_id': verify_quotation.id,
                                            'in_system_quotation_number': verify_quotation.name,
                                            'migration_date': fields.Datetime.now(),
                                            'error_message': False,
                                        })
                                        cr.commit()
                                        # Re-browse to get fresh data from database
                                        quotation_to_process = env['eq.migration.quotation'].browse(quotation_to_process.id)
                                        migrating_quotation = f"{quotation_number} - DONE"
                                        _logger.info("✅ Quotation %s status corrected to migrated", quotation_number)
                                    else:
                                        # Quotation doesn't exist - real error
                                        migrating_quotation = f"{quotation_number} - ERROR"
                                        error_detail = quotation_to_process.error_message or quotation_to_process.status_message or 'Unknown error'
                                        _logger.warning("❌ Quotation %s failed: %s", quotation_number, error_detail[:100])
                                        # Log failed migration to file for later processing
                                        _log_failed_migration(quotation_number, error_detail)
                                elif quotation_to_process.status == 'migrated':
                                    if 'already existed' not in migrating_quotation:
                                        migrating_quotation = f"{quotation_number} - DONE"
                                    _logger.info("✅ Successfully migrated quotation %s", quotation_number)
                                else:
                                    migrating_quotation = f"{quotation_number} - {quotation_to_process.status}"
                                    _logger.warning("Quotation %s status: %s", quotation_number, quotation_to_process.status)
                            except Exception as migrate_error:
                                error_msg = str(migrate_error)
                                _logger.error("Failed to migrate quotation %s: %s", quotation_number, error_msg, exc_info=True)
                                
                                # Before marking as error, check if quotation was actually created
                                verify_quotation = env['sale.order'].search([
                                    ('name', '=', quotation_number)
                                ], limit=1)
                                
                                if verify_quotation:
                                    # Quotation was created! Update status to migrated
                                    _logger.info("Quotation %s was created despite exception, updating status to migrated", quotation_number)
                                    quotation_to_process.write({
                                        'status': 'migrated',
                                        'status_message': 'Successfully migrated (created despite exception)',
                                        'odoo19_quotation_id': verify_quotation.id,
                                        'in_system_quotation_number': verify_quotation.name,
                                        'migration_date': fields.Datetime.now(),
                                        'error_message': False,
                                    })
                                    cr.commit()
                                    migrating_quotation = f"{quotation_number} - DONE"
                                    _logger.info("✅ Quotation %s marked as migrated (was created successfully)", quotation_number)
                                else:
                                    # Quotation was NOT created - this is a real error
                                    try:
                                        quotation_to_process.write({
                                            'status': 'error',
                                            'status_message': f'Migration error: {error_msg[:100]}',
                                            'error_message': error_msg[:500],
                                        })
                                        cr.commit()
                                    except:
                                        # If write fails, try direct SQL update
                                        try:
                                            cr.execute(
                                                "UPDATE eq_migration_quotation SET status='error', status_message=%s, error_message=%s WHERE id=%s",
                                                (f'Migration error: {error_msg[:100]}', error_msg[:500], quotation_to_process.id)
                                            )
                                            cr.commit()
                                        except:
                                            pass
                                    
                                    migrating_quotation = f"{quotation_number} - ERROR"
                                    # Log failed migration to file for later processing
                                    _log_failed_migration(quotation_number, error_msg)
                    except Exception as e:
                        _logger.error("Error processing quotation %s: %s", 
                                    quotation_to_process.uploaded_quotation_number if quotation_to_process else 'N/A', 
                                    str(e), exc_info=True)
                        # Update status to error
                        if quotation_to_process:
                            try:
                                quotation_to_process.write({
                                    'status': 'error',
                                    'status_message': f'Cron error: {str(e)[:100]}',
                                    'error_message': str(e)[:500],
                                })
                                cr.commit()
                            except:
                                pass
                        migrating_quotation = f"Error: {str(e)[:50]}"
                elif currently_migrating:
                    migrating_quotation = f"{currently_migrating.uploaded_quotation_number} (in progress)"
                
                # Re-count queued at the end to ensure accurate count
                total_queued = env['eq.migration.quotation'].search_count([
                    ('status', '=', 'queued')
                ])
                _logger.info("Final queued count: %s (status='queued')", total_queued)
                
                # Build response
                response_lines = [
                    f"Total Queued: {total_queued}",
                    f"Migrating Now: {migrating_quotation}",
                    "DONE"
                ]
                
                return request.make_response(
                    '\n'.join(response_lines),
                    headers=[
                        ('Content-Type', 'text/plain; charset=utf-8'),
                    ]
                )
            finally:
                cr.close()
            
        except Exception as e:
            _logger.error("Error in migration cron controller: %s", str(e), exc_info=True)
            return request.make_response(
                f"ERROR: {str(e)}\n",
                headers=[
                    ('Content-Type', 'text/plain; charset=utf-8'),
                ]
            )

    @http.route('/migration/status', type='http', auth='public', methods=['GET'], csrf=False)
    def get_status(self, **kwargs):
        """
        Get current migration status without processing.
        Returns JSON with detailed status.
        
        Usage: /migration/status?db=your_database_name
        """
        try:
            # Get database from query parameter
            # In Odoo, query string parameters are passed as kwargs
            db = kwargs.get('db')
            
            # Fallback: parse from URL if not in kwargs
            if not db and hasattr(request, 'httprequest') and request.httprequest:
                from urllib.parse import parse_qs, urlparse
                try:
                    parsed = urlparse(request.httprequest.url)
                    query_params = parse_qs(parsed.query)
                    if 'db' in query_params:
                        db = query_params['db'][0]
                except:
                    pass
            
            if not db:
                import json
                return request.make_response(
                    json.dumps({'error': 'Database not specified. Use: /migration/status?db=your_database_name'}),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            
            # Create environment with specified database
            from odoo.api import Environment
            from odoo import sql_db
            try:
                # Get database connection
                db_conn = sql_db.db_connect(db)
                cr = db_conn.cursor()
            except Exception as reg_error:
                import json
                return request.make_response(
                    json.dumps({'error': f'Database "{db}" not found: {str(reg_error)}'}),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            
            try:
                env = Environment(cr, 1, {})  # Use user 1 (admin)
                
                MigrationQuotation = env['eq.migration.quotation']
                
                # Get counts by status - ONLY count 'queued' status
                total_queued = MigrationQuotation.search_count([
                    ('status', '=', 'queued')
                ])
                
                currently_migrating = MigrationQuotation.search([
                    ('status', '=', 'migrating')
                ], limit=1, order='write_date desc')
                
                migrating_quotation = currently_migrating.uploaded_quotation_number if currently_migrating else None
                
                total_migrated = MigrationQuotation.search_count([
                    ('status', '=', 'migrated')
                ])
                
                total_errors = MigrationQuotation.search_count([
                    ('status', '=', 'error')
                ])
                
                import json
                status_data = {
                    'total_queued': total_queued,
                    'migrating_now': migrating_quotation,
                    'total_migrated': total_migrated,
                    'total_errors': total_errors,
                }
                
                return request.make_response(
                    json.dumps(status_data, indent=2),
                    headers=[
                        ('Content-Type', 'application/json; charset=utf-8'),
                    ]
                )
            finally:
                cr.close()
            
        except Exception as e:
            _logger.error("Error in migration status: %s", str(e), exc_info=True)
            import json
            return request.make_response(
                json.dumps({'error': str(e)}),
                headers=[
                    ('Content-Type', 'application/json; charset=utf-8'),
                ]
            )

    @http.route('/migration/process_one_estimation', type='http', auth='public', methods=['GET'], csrf=False)
    def process_one_estimation(self, **kwargs):
        """
        Process one estimation from the queue.
        Can be called repeatedly like a cron job.
        
        Returns simple text response with status.
        
        Usage: /migration/process_one_estimation?db=your_database_name
        """
        _logger.info("=" * 50)
        _logger.info("process_one_estimation ROUTE CALLED!")
        _logger.info("URL: %s", request.httprequest.url if hasattr(request, 'httprequest') and request.httprequest else 'N/A')
        _logger.info("kwargs: %s", kwargs)
        _logger.info("=" * 50)
        try:
            # Get database from query parameter
            db = kwargs.get('db')
            
            # Fallback: parse from URL if not in kwargs
            if not db and hasattr(request, 'httprequest') and request.httprequest:
                from urllib.parse import parse_qs, urlparse
                try:
                    parsed = urlparse(request.httprequest.url)
                    query_params = parse_qs(parsed.query)
                    if 'db' in query_params:
                        db = query_params['db'][0]
                except:
                    pass
            
            if not db:
                return request.make_response(
                    'ERROR: Database not specified. Use: /migration/process_one_estimation?db=your_database_name\n',
                    headers=[('Content-Type', 'text/plain; charset=utf-8')]
                )
            
            # Create environment with specified database
            from odoo.api import Environment
            from odoo import sql_db
            try:
                db_conn = sql_db.db_connect(db)
                cr = db_conn.cursor()
            except Exception as reg_error:
                return request.make_response(
                    f'ERROR: Database "{db}" not found: {str(reg_error)}\n',
                    headers=[('Content-Type', 'text/plain; charset=utf-8')]
                )
            
            try:
                env = Environment(cr, 1, {})  # Use user 1 (admin)
                
                # Get estimation migration model
                MigrationEstimation = env['estimation.migration.line']
            
                # Count total queued
                total_queued = MigrationEstimation.search_count([
                    ('status', '=', 'queued')
                ])
                _logger.info("Total queued estimations: %s (status='queued')", total_queued)
                
                # Check for stuck migrations (migrating for more than 30 seconds)
                from datetime import timedelta
                stuck_threshold = fields.Datetime.now() - timedelta(seconds=30)
                
                # Find ALL migrating records
                all_migrating = MigrationEstimation.search([
                    ('status', '=', 'migrating')
                ])
                
                # Reset stuck migrations back to error
                stuck_count = 0
                for migrating_record in all_migrating:
                    if migrating_record.write_date and migrating_record.write_date < stuck_threshold:
                        stuck_seconds = int((fields.Datetime.now() - migrating_record.write_date).total_seconds())
                        _logger.warning("Found stuck estimation migration: %s (stuck for %s seconds), resetting to error", 
                                      migrating_record.uploaded_estimation_number,
                                      stuck_seconds)
                        migrating_record.write({
                            'status': 'error',
                            'status_message': 'Migration stuck - reset to error',
                            'error_message': f'Migration was stuck in migrating status for {stuck_seconds} seconds. Last update: {migrating_record.write_date}',
                        })
                        stuck_count += 1
                
                if stuck_count > 0:
                    cr.commit()
                    _logger.warning("Reset %s stuck estimation migration(s) to error status", stuck_count)
                
                # Find currently migrating (recent ones, not stuck)
                currently_migrating = MigrationEstimation.search([
                    ('status', '=', 'migrating'),
                    ('write_date', '>=', stuck_threshold)
                ], limit=1, order='write_date desc')
                
                migrating_estimation = 'None'
                
                # If nothing is migrating, get the first queued one and process it SYNCHRONOUSLY
                estimation_to_process = None
                if not currently_migrating:
                    estimation_to_process = MigrationEstimation.search([
                        ('status', '=', 'queued')
                    ], limit=1, order='id asc')
                
                # Process one estimation SYNCHRONOUSLY if available
                if estimation_to_process and not currently_migrating:
                    try:
                        if estimation_to_process.status != 'queued':
                            migrating_estimation = f"Skipped: {estimation_to_process.status} (not queued)"
                        else:
                            estimation_number = estimation_to_process.uploaded_estimation_number
                            _logger.info("🔄 Starting SYNCHRONOUS migration for estimation %s", estimation_number)
                            
                            # Set status to pending_migration first (action_migrate requires it)
                            estimation_to_process.write({
                                'status': 'pending_migration',
                                'status_message': 'Starting migration...',
                            })
                            cr.commit()
                            migrating_estimation = estimation_number
                            
                            # Call action_migrate directly (synchronous)
                            try:
                                # Check if estimation already exists in Odoo 19
                                existing_estimation = env['fm.amc.estimation'].search([
                                    ('name', '=', estimation_number)
                                ], limit=1)
                                
                                if existing_estimation:
                                    if estimation_to_process.status in ('queued', 'pending_migration'):
                                        _logger.info("Estimation %s already exists in Odoo 19 (ID: %s), updating status to migrated", 
                                                   estimation_number, existing_estimation.id)
                                        estimation_to_process.write({
                                            'status': 'migrated',
                                            'status_message': 'Already migrated (existed in system)',
                                            'odoo19_estimation_id': existing_estimation.id,
                                            'in_system_estimation_number': existing_estimation.name,
                                            'migration_date': fields.Datetime.now(),
                                            'error_message': False,
                                        })
                                        cr.commit()
                                        migrating_estimation = f"{estimation_number} - DONE (already existed)"
                                        _logger.info("✅ Estimation %s marked as migrated (already existed)", estimation_number)
                                    else:
                                        migrating_estimation = f"{estimation_number} - Already migrated"
                                else:
                                    # Proceed with migration
                                    try:
                                        result = estimation_to_process.action_migrate()
                                        cr.commit()
                                    except Exception as migrate_exception:
                                        error_msg = str(migrate_exception)
                                        _logger.warning("action_migrate raised exception for %s: %s - checking if estimation was created", 
                                                      estimation_number, error_msg[:100])
                                        
                                        # Check if estimation was actually created
                                        created_estimation = env['fm.amc.estimation'].search([
                                            ('name', '=', estimation_number)
                                        ], limit=1)
                                        
                                        if created_estimation:
                                            _logger.info("Estimation %s was created successfully despite exception, updating status to migrated", estimation_number)
                                            estimation_to_process.write({
                                                'status': 'migrated',
                                                'status_message': 'Successfully migrated (created despite exception)',
                                                'odoo19_estimation_id': created_estimation.id,
                                                'in_system_estimation_number': created_estimation.name,
                                                'migration_date': fields.Datetime.now(),
                                                'error_message': False,
                                            })
                                            cr.commit()
                                            migrating_estimation = f"{estimation_number} - DONE"
                                        else:
                                            raise  # Re-raise if not created
                                
                                # Refresh status - re-browse to get fresh data from database
                                estimation_to_process.invalidate_recordset(['status', 'error_message', 'status_message'])
                                estimation_to_process = env['estimation.migration.line'].browse(estimation_to_process.id)
                                
                                # Re-count queued
                                total_queued = MigrationEstimation.search_count([
                                    ('status', '=', 'queued')
                                ])
                                
                                # Verify status and fix if needed
                                if estimation_to_process.status == 'error':
                                    verify_estimation = env['fm.amc.estimation'].search([
                                        ('name', '=', estimation_number)
                                    ], limit=1)
                                    
                                    if verify_estimation:
                                        _logger.info("Estimation %s exists but status is 'error', fixing to 'migrated'", estimation_number)
                                        estimation_to_process.write({
                                            'status': 'migrated',
                                            'status_message': 'Successfully migrated (verified)',
                                            'odoo19_estimation_id': verify_estimation.id,
                                            'in_system_estimation_number': verify_estimation.name,
                                            'migration_date': fields.Datetime.now(),
                                            'error_message': False,
                                        })
                                        cr.commit()
                                        migrating_estimation = f"{estimation_number} - DONE"
                                    else:
                                        migrating_estimation = f"{estimation_number} - ERROR"
                                        error_detail = estimation_to_process.error_message or estimation_to_process.status_message or 'Unknown error'
                                        _logger.warning("❌ Estimation %s failed: %s", estimation_number, error_detail[:100])
                                        # Log failed migration
                                        _log_failed_estimation_migration(estimation_number, error_detail)
                                elif estimation_to_process.status == 'migrated':
                                    if 'already existed' not in migrating_estimation:
                                        migrating_estimation = f"{estimation_number} - DONE"
                                    _logger.info("✅ Successfully migrated estimation %s", estimation_number)
                                else:
                                    migrating_estimation = f"{estimation_number} - {estimation_to_process.status}"
                                    
                            except Exception as migrate_error:
                                error_msg = str(migrate_error)
                                _logger.error("Failed to migrate estimation %s: %s", estimation_number, error_msg, exc_info=True)
                                
                                # Check if estimation was actually created
                                verify_estimation = env['fm.amc.estimation'].search([
                                    ('name', '=', estimation_number)
                                ], limit=1)
                                
                                if verify_estimation:
                                    _logger.info("Estimation %s was created despite exception, updating status to migrated", estimation_number)
                                    estimation_to_process.write({
                                        'status': 'migrated',
                                        'status_message': 'Successfully migrated (created despite exception)',
                                        'odoo19_estimation_id': verify_estimation.id,
                                        'in_system_estimation_number': verify_estimation.name,
                                        'migration_date': fields.Datetime.now(),
                                        'error_message': False,
                                    })
                                    cr.commit()
                                    migrating_estimation = f"{estimation_number} - DONE"
                                else:
                                    # Real error - log it
                                    try:
                                        estimation_to_process.write({
                                            'status': 'error',
                                            'status_message': f'Migration error: {error_msg[:100]}',
                                            'error_message': error_msg[:500],
                                        })
                                        cr.commit()
                                    except:
                                        try:
                                            cr.execute(
                                                "UPDATE estimation_migration_line SET status='error', status_message=%s, error_message=%s WHERE id=%s",
                                                (f'Migration error: {error_msg[:100]}', error_msg[:500], estimation_to_process.id)
                                            )
                                            cr.commit()
                                        except:
                                            pass
                                    
                                    migrating_estimation = f"{estimation_number} - ERROR"
                                    # Log failed migration
                                    _log_failed_estimation_migration(estimation_number, error_msg)
                    except Exception as e:
                        _logger.error("Error processing estimation %s: %s", 
                                    estimation_to_process.uploaded_estimation_number if estimation_to_process else 'N/A', 
                                    str(e), exc_info=True)
                        if estimation_to_process:
                            try:
                                estimation_to_process.write({
                                    'status': 'error',
                                    'status_message': f'Cron error: {str(e)[:100]}',
                                    'error_message': str(e)[:500],
                                })
                                cr.commit()
                                # Log failed migration
                                _log_failed_estimation_migration(
                                    estimation_to_process.uploaded_estimation_number, 
                                    str(e)
                                )
                            except:
                                pass
                        migrating_estimation = f"Error: {str(e)[:50]}"
                elif currently_migrating:
                    migrating_estimation = f"{currently_migrating.uploaded_estimation_number} (in progress)"
                
                # Re-count queued at the end
                total_queued = MigrationEstimation.search_count([
                    ('status', '=', 'queued')
                ])
                _logger.info("Final queued count: %s (status='queued')", total_queued)
                
                # Build response
                response_lines = [
                    f"Total Queued: {total_queued}",
                    f"Migrating Now: {migrating_estimation}",
                    "DONE"
                ]
                
                return request.make_response(
                    '\n'.join(response_lines),
                    headers=[
                        ('Content-Type', 'text/plain; charset=utf-8'),
                    ]
                )
            finally:
                cr.close()
            
        except Exception as e:
            _logger.error("Error in estimation migration cron controller: %s", str(e), exc_info=True)
            return request.make_response(
                f"ERROR: {str(e)}\n",
                headers=[
                    ('Content-Type', 'text/plain; charset=utf-8'),
                ]
            )

    @http.route('/migration/status_estimation', type='http', auth='public', methods=['GET'], csrf=False)
    def get_estimation_status(self, **kwargs):
        """
        Get current estimation migration status without processing.
        Returns JSON with detailed status.
        
        Usage: /migration/status_estimation?db=your_database_name
        """
        try:
            db = kwargs.get('db')
            
            if not db and hasattr(request, 'httprequest') and request.httprequest:
                from urllib.parse import parse_qs, urlparse
                try:
                    parsed = urlparse(request.httprequest.url)
                    query_params = parse_qs(parsed.query)
                    if 'db' in query_params:
                        db = query_params['db'][0]
                except:
                    pass
            
            if not db:
                import json
                return request.make_response(
                    json.dumps({'error': 'Database not specified. Use: /migration/status_estimation?db=your_database_name'}),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            
            from odoo.api import Environment
            from odoo import sql_db
            try:
                db_conn = sql_db.db_connect(db)
                cr = db_conn.cursor()
            except Exception as reg_error:
                import json
                return request.make_response(
                    json.dumps({'error': f'Database "{db}" not found: {str(reg_error)}'}),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            
            try:
                env = Environment(cr, 1, {})
                
                MigrationEstimation = env['estimation.migration.line']
                
                total_queued = MigrationEstimation.search_count([
                    ('status', '=', 'queued')
                ])
                
                currently_migrating = MigrationEstimation.search([
                    ('status', '=', 'migrating')
                ], limit=1, order='write_date desc')
                
                migrating_estimation = currently_migrating.uploaded_estimation_number if currently_migrating else None
                
                total_migrated = MigrationEstimation.search_count([
                    ('status', '=', 'migrated')
                ])
                
                total_errors = MigrationEstimation.search_count([
                    ('status', '=', 'error')
                ])
                
                import json
                status_data = {
                    'total_queued': total_queued,
                    'migrating_now': migrating_estimation,
                    'total_migrated': total_migrated,
                    'total_errors': total_errors,
                }
                
                return request.make_response(
                    json.dumps(status_data, indent=2),
                    headers=[
                        ('Content-Type', 'application/json; charset=utf-8'),
                    ]
                )
            finally:
                cr.close()
            
        except Exception as e:
            _logger.error("Error in estimation migration status: %s", str(e), exc_info=True)
            import json
            return request.make_response(
                json.dumps({'error': str(e)}),
                headers=[
                    ('Content-Type', 'application/json; charset=utf-8'),
                ]
            )

    @http.route('/migration/process_one_rfq', type='http', auth='public', methods=['GET'], csrf=False)
    def process_one_rfq(self, **kwargs):
        """
        Process one RFQ from the queue.
        Can be called repeatedly like a cron job.
        
        Returns simple text response with status.
        
        Usage: /migration/process_one_rfq?db=your_database_name
        """
        _logger.info("=" * 50)
        _logger.info("process_one_rfq ROUTE CALLED!")
        _logger.info("URL: %s", request.httprequest.url if hasattr(request, 'httprequest') and request.httprequest else 'N/A')
        _logger.info("kwargs: %s", kwargs)
        _logger.info("=" * 50)
        try:
            # Get database from query parameter
            db = kwargs.get('db')
            
            # Fallback: parse from URL if not in kwargs
            if not db and hasattr(request, 'httprequest') and request.httprequest:
                from urllib.parse import parse_qs, urlparse
                try:
                    parsed = urlparse(request.httprequest.url)
                    query_params = parse_qs(parsed.query)
                    if 'db' in query_params:
                        db = query_params['db'][0]
                except:
                    pass
            
            if not db:
                return request.make_response(
                    'ERROR: Database not specified. Use: /migration/process_one_rfq?db=your_database_name\n',
                    headers=[('Content-Type', 'text/plain; charset=utf-8')]
                )
            
            # Create environment with specified database
            from odoo.api import Environment
            from odoo import sql_db
            try:
                db_conn = sql_db.db_connect(db)
                cr = db_conn.cursor()
            except Exception as reg_error:
                return request.make_response(
                    f'ERROR: Database "{db}" not found: {str(reg_error)}\n',
                    headers=[('Content-Type', 'text/plain; charset=utf-8')]
                )
            
            try:
                env = Environment(cr, 1, {})  # Use user 1 (admin)
                
                # Get RFQ migration model
                MigrationRFQ = env['rfq.migration.line']
            
                # Count total queued
                total_queued = MigrationRFQ.search_count([
                    ('status', '=', 'queued')
                ])
                _logger.info("Total queued RFQs: %s (status='queued')", total_queued)
                
                # Check for stuck migrations (migrating for more than 30 seconds)
                from datetime import timedelta
                stuck_threshold = fields.Datetime.now() - timedelta(seconds=30)
                
                # Reset stuck migrations using the model method
                reset_result = MigrationRFQ.action_reset_stuck_migrations(stuck_threshold_seconds=30)
                if reset_result['reset_count'] > 0:
                    cr.commit()
                
                # Find currently migrating (recent ones, not stuck)
                currently_migrating = MigrationRFQ.search([
                    ('status', '=', 'migrating'),
                    ('write_date', '>=', stuck_threshold)
                ], limit=1, order='write_date desc')
                
                migrating_rfq = 'None'
                
                # If nothing is migrating, get the first queued one and process it SYNCHRONOUSLY
                rfq_to_process = None
                if not currently_migrating:
                    rfq_to_process = MigrationRFQ.search([
                        ('status', '=', 'queued')
                    ], limit=1, order='id asc')
                    
                    if rfq_to_process:
                        rfq_number = rfq_to_process.uploaded_rfq_number
                        _logger.info("Processing RFQ: %s", rfq_number)
                        
                        # Log ALL details from migration table BEFORE migration starts
                        _logger.info("=" * 80)
                        _logger.info("📋 RFQ MIGRATION LINE DETAILS (BEFORE MIGRATION)")
                        _logger.info("=" * 80)
                        _logger.info("RFQ Number: %s", rfq_to_process.uploaded_rfq_number)
                        _logger.info("Priority: %s", rfq_to_process.priority or 'N/A')
                        _logger.info("Vendor: %s", rfq_to_process.vendor or 'N/A')
                        _logger.info("Project: %s", rfq_to_process.project or 'N/A')
                        _logger.info("Purchase Representative: %s", rfq_to_process.purchase_representative or 'N/A')
                        _logger.info("Order Deadline: %s", rfq_to_process.order_deadline or 'N/A')
                        _logger.info("Status (Excel): %s", rfq_to_process.excel_status or 'N/A')
                        _logger.info("Branch/ID: %s", rfq_to_process.company or 'N/A')
                        _logger.info("Stage: %s", rfq_to_process.stage or 'N/A')
                        _logger.info("Bills/Number: %s", rfq_to_process.bills_number or 'N/A')
                        _logger.info("Bills/ID: %s", rfq_to_process.odoo14_bill_ids or 'N/A')
                        _logger.info("Created On: %s", rfq_to_process.created_on or 'N/A')
                        _logger.info("Effective Date: %s", rfq_to_process.effective_date or 'N/A')
                        _logger.info("Receipt Date: %s", rfq_to_process.receipt_date or 'N/A')
                        _logger.info("Current Status: %s", rfq_to_process.status)
                        _logger.info("=" * 80)
                        
                        try:
                            # Check if RFQ already exists
                            existing_rfq = env['purchase.order'].search([
                                ('name', '=', rfq_number)
                            ], limit=1)
                            
                            if existing_rfq:
                                rfq_to_process.write({
                                    'status': 'migrated',
                                    'status_message': 'Already migrated (existed in system)',
                                    'odoo19_rfq_id': existing_rfq.id,
                                    'in_system_rfq_number': existing_rfq.name,
                                    'migration_date': fields.Datetime.now(),
                                    'error_message': False,
                                })
                                cr.commit()
                                migrating_rfq = f"{rfq_number} - DONE (already existed)"
                                _logger.info("✅ RFQ %s marked as migrated (already existed)", rfq_number)
                            else:
                                # Process migration
                                result = rfq_to_process.action_migrate()
                                cr.commit()
                                
                                # Refresh to get actual status
                                rfq_to_process.invalidate_recordset(['status', 'error_message', 'status_message'])
                                rfq_to_process = env['rfq.migration.line'].browse(rfq_to_process.id)
                                
                                if rfq_to_process.status == 'migrated':
                                    migrating_rfq = f"{rfq_number} - DONE"
                                    _logger.info("✅ RFQ %s migrated successfully", rfq_number)
                                elif rfq_to_process.status == 'error':
                                    error_detail = rfq_to_process.error_message or rfq_to_process.status_message or 'Unknown error'
                                    migrating_rfq = f"{rfq_number} - ERROR"
                                    _logger.warning("❌ RFQ %s failed: %s", rfq_number, error_detail[:100])
                                    _log_failed_rfq_migration(rfq_number, error_detail)
                                else:
                                    migrating_rfq = f"{rfq_number} - in progress"
                        except Exception as migrate_error:
                            error_msg = str(migrate_error)
                            _logger.error("Failed to migrate RFQ %s: %s", rfq_number, error_msg, exc_info=True)
                            
                            # Check if RFQ was actually created
                            verify_rfq = env['purchase.order'].search([
                                ('name', '=', rfq_number)
                            ], limit=1)
                            
                            if verify_rfq:
                                _logger.info("RFQ %s was created despite exception, updating status to migrated", rfq_number)
                                rfq_to_process.write({
                                    'status': 'migrated',
                                    'status_message': 'Successfully migrated (created despite exception)',
                                    'odoo19_rfq_id': verify_rfq.id,
                                    'in_system_rfq_number': verify_rfq.name,
                                    'migration_date': fields.Datetime.now(),
                                    'error_message': False,
                                })
                                cr.commit()
                                migrating_rfq = f"{rfq_number} - DONE"
                            else:
                                # Real error - log it
                                try:
                                    rfq_to_process.write({
                                        'status': 'error',
                                        'status_message': f'Migration error: {error_msg[:100]}',
                                        'error_message': error_msg[:500],
                                    })
                                    cr.commit()
                                except:
                                    try:
                                        cr.execute(
                                            "UPDATE rfq_migration_line SET status='error', status_message=%s, error_message=%s WHERE id=%s",
                                            (f'Migration error: {error_msg[:100]}', error_msg[:500], rfq_to_process.id)
                                        )
                                        cr.commit()
                                    except:
                                        pass
                                
                                migrating_rfq = f"{rfq_number} - ERROR"
                                _log_failed_rfq_migration(rfq_number, error_msg)
                elif currently_migrating:
                    migrating_rfq = f"{currently_migrating.uploaded_rfq_number} (in progress)"
                
                # Re-count queued at the end
                total_queued = MigrationRFQ.search_count([
                    ('status', '=', 'queued')
                ])
                _logger.info("Final queued count: %s (status='queued')", total_queued)
                
                # Build response with RFQ details if available
                response_lines = [
                    f"Total Queued: {total_queued}",
                    f"Migrating Now: {migrating_rfq}",
                ]
                
                # Add RFQ migration line details if we have one to process or currently migrating
                rfq_for_details = rfq_to_process or currently_migrating
                if rfq_for_details:
                    response_lines.append("RFQ_DETAILS_START")
                    response_lines.append(f"RFQ_Number: {rfq_for_details.uploaded_rfq_number}")
                    response_lines.append(f"Priority: {rfq_for_details.priority or 'N/A'}")
                    response_lines.append(f"Vendor: {rfq_for_details.vendor or 'N/A'}")
                    response_lines.append(f"Project: {rfq_for_details.project or 'N/A'}")
                    response_lines.append(f"Purchase_Representative: {rfq_for_details.purchase_representative or 'N/A'}")
                    response_lines.append(f"Order_Deadline: {rfq_for_details.order_deadline or 'N/A'}")
                    response_lines.append(f"Status_Excel: {rfq_for_details.excel_status or 'N/A'}")
                    response_lines.append(f"Branch_ID: {rfq_for_details.company or 'N/A'}")
                    response_lines.append(f"Stage: {rfq_for_details.stage or 'N/A'}")
                    response_lines.append(f"Bills_Number: {rfq_for_details.bills_number or 'N/A'}")
                    response_lines.append(f"Bills_ID: {rfq_for_details.odoo14_bill_ids or 'N/A'}")
                    response_lines.append(f"Created_On: {rfq_for_details.created_on or 'N/A'}")
                    response_lines.append(f"Effective_Date: {rfq_for_details.effective_date or 'N/A'}")
                    response_lines.append(f"Receipt_Date: {rfq_for_details.receipt_date or 'N/A'}")
                    response_lines.append(f"Current_Status: {rfq_for_details.status}")
                    response_lines.append("RFQ_DETAILS_END")
                
                response_lines.append("DONE")
                
                return request.make_response(
                    '\n'.join(response_lines),
                    headers=[
                        ('Content-Type', 'text/plain; charset=utf-8'),
                    ]
                )
            finally:
                cr.close()
            
        except Exception as e:
            _logger.error("Error in RFQ migration cron controller: %s", str(e), exc_info=True)
            return request.make_response(
                f"ERROR: {str(e)}\n",
                headers=[
                    ('Content-Type', 'text/plain; charset=utf-8'),
                ]
            )

    @http.route('/migration/rfq_details', type='http', auth='public', methods=['GET'], csrf=False)
    def get_rfq_details(self, **kwargs):
        """
        Get detailed RFQ migration information including Purchase Order, Vendor Bills, and Payments.
        Returns JSON with detailed status.
        
        Usage: /migration/rfq_details?db=your_database_name&rfq_number=MFS-AUH-3578
        """
        try:
            db = kwargs.get('db')
            rfq_number = kwargs.get('rfq_number')
            
            if not db and hasattr(request, 'httprequest') and request.httprequest:
                from urllib.parse import parse_qs, urlparse
                try:
                    parsed = urlparse(request.httprequest.url)
                    query_params = parse_qs(parsed.query)
                    if 'db' in query_params:
                        db = query_params['db'][0]
                    if 'rfq_number' in query_params:
                        rfq_number = query_params['rfq_number'][0]
                except:
                    pass
            
            if not db:
                import json
                return request.make_response(
                    json.dumps({'error': 'Database not specified'}),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            
            if not rfq_number:
                import json
                return request.make_response(
                    json.dumps({'error': 'RFQ number not specified'}),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            
            from odoo.api import Environment
            from odoo import sql_db
            try:
                db_conn = sql_db.db_connect(db)
                cr = db_conn.cursor()
            except Exception as reg_error:
                import json
                return request.make_response(
                    json.dumps({'error': f'Database "{db}" not found: {str(reg_error)}'}),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            
            try:
                env = Environment(cr, 1, {})
                
                # First check migration line to get odoo19_rfq_id if available
                migration_line = env['rfq.migration.line'].search([
                    ('uploaded_rfq_number', '=', rfq_number)
                ], limit=1, order='id desc')
                
                purchase_order = None
                if migration_line:
                    # First try: Use the stored ID from migration
                    if migration_line.odoo19_rfq_id:
                        # Ensure we have a single integer ID, not a recordset
                        po_id = migration_line.odoo19_rfq_id
                        if isinstance(po_id, (list, tuple)):
                            po_id = po_id[0] if po_id else None
                        if po_id:
                            purchase_order = env['purchase.order'].browse(po_id)
                            if not purchase_order.exists():
                                purchase_order = None
                                _logger.warning("Migration line has odoo19_rfq_id=%s but Purchase Order doesn't exist", po_id)
                    
                    # Second try: Search by in_system_rfq_number if available
                    if not purchase_order and migration_line.in_system_rfq_number:
                        purchase_order = env['purchase.order'].search([
                            ('name', '=', migration_line.in_system_rfq_number)
                        ], limit=1)
                        if purchase_order:
                            _logger.info("Found Purchase Order by in_system_rfq_number: %s", migration_line.in_system_rfq_number)
                
                # Third try: Search by uploaded_rfq_number (exact match)
                if not purchase_order:
                    purchase_order = env['purchase.order'].search([
                        ('name', '=', rfq_number)
                    ], limit=1)
                    if purchase_order:
                        _logger.info("Found Purchase Order by name: %s", rfq_number)
                
                # Fourth try: Search by partial match (in case name changed)
                if not purchase_order:
                    purchase_order = env['purchase.order'].search([
                        ('name', 'ilike', rfq_number)
                    ], limit=1)
                    if purchase_order:
                        _logger.info("Found Purchase Order by partial name match: %s -> %s", rfq_number, purchase_order.name)
                
                result = {
                    'rfq_number': rfq_number,
                    'has_purchase_order': False,
                    'purchase_order_state': None,
                    'purchase_order_id': None,
                    'is_confirmed': False,
                    'vendor_bills': [],
                    'payments': [],
                }
                
                if purchase_order:
                    # Ensure purchase_order is a single recordset (not multiple)
                    if len(purchase_order) > 1:
                        purchase_order = purchase_order[0]
                        _logger.warning("Multiple Purchase Orders found, using first one: %s", purchase_order.id)
                    
                    # Extract ID to avoid SQL adaptation errors
                    po_id = purchase_order.id if hasattr(purchase_order, 'id') else None
                    if not po_id:
                        _logger.error("Purchase Order has no ID, skipping")
                        purchase_order = None
                    else:
                        _logger.info("✅ Found Purchase Order for RFQ %s: ID=%s, Name=%s, State=%s, Stage=%s", 
                                   rfq_number, po_id, purchase_order.name, purchase_order.state,
                                   purchase_order.rfq_stage_id.name if hasattr(purchase_order, 'rfq_stage_id') and purchase_order.rfq_stage_id else 'N/A')
                        result['has_purchase_order'] = True
                        result['purchase_order_state'] = purchase_order.state
                        result['purchase_order_id'] = po_id
                        result['is_confirmed'] = purchase_order.state in ('purchase', 'done')
                        result['rfq_stage'] = purchase_order.rfq_stage_id.name if hasattr(purchase_order, 'rfq_stage_id') and purchase_order.rfq_stage_id else 'Draft'
                    
                    # Get billing status
                    if hasattr(purchase_order, 'billing_status'):
                        result['billing_status'] = purchase_order.billing_status
                    elif hasattr(purchase_order, 'invoice_status'):
                        # Map invoice_status to billing_status
                        invoice_status = purchase_order.invoice_status
                        if invoice_status == 'no':
                            result['billing_status'] = 'nothing_to_bill'
                        elif invoice_status == 'to invoice':
                            result['billing_status'] = 'to_bill'
                        elif invoice_status == 'invoiced':
                            result['billing_status'] = 'billed'
                        else:
                            result['billing_status'] = 'nothing_to_bill'
                    else:
                        result['billing_status'] = 'unknown'
                    
                    # Get bill numbers from migration line (queue list) - PRIMARY SOURCE
                    bill_numbers_from_queue = []
                    bill_ids_from_queue = []
                    if migration_line:
                        if migration_line.bills_number:
                            # Parse comma-separated bill numbers
                            bill_numbers_from_queue = [b.strip() for b in migration_line.bills_number.split(',') if b.strip()]
                        if migration_line.odoo14_bill_ids:
                            # Parse comma-separated bill IDs
                            bill_ids_from_queue = [b.strip() for b in migration_line.odoo14_bill_ids.split(',') if b.strip()]
                            _logger.info("📋 Queue list has bill IDs: %s", bill_ids_from_queue)
                    
                    # Get vendor bills (account.move) - from Purchase Order
                    # Use the extracted po_id to avoid SQL adaptation errors
                    vendor_bills = env['account.move'].search([
                        ('purchase_id', '=', po_id),
                        ('move_type', 'in', ('in_invoice', 'in_refund'))
                    ])
                    
                    # Add bill numbers and IDs from queue list to result
                    result['bill_numbers_from_queue'] = bill_numbers_from_queue
                    result['bill_ids_from_queue'] = bill_ids_from_queue
                    
                    # Also add bill IDs from migrated bills if available
                    if vendor_bills and not bill_ids_from_queue:
                        # Extract IDs from migrated bills
                        migrated_bill_ids = [str(bill.id) for bill in vendor_bills]
                        result['bill_ids_from_queue'] = migrated_bill_ids
                    
                    for bill in vendor_bills:
                        bill_info = {
                            'name': bill.name,
                            'state': bill.state,
                            'amount_total': bill.amount_total,
                            'id': bill.id,
                        }
                        
                        # Get payments for this bill
                        payments = []
                        if bill.state == 'posted':
                            # Find account.payment records linked to this invoice
                            if 'account.payment' in env.registry:
                                linked_payments = env['account.payment'].search([
                                    ('state', '=', 'posted'),
                                    ('reconciled_invoice_ids', 'in', bill.id)
                                ])
                                
                                for payment in linked_payments:
                                    payment_info = {
                                        'name': payment.name,
                                        'date': str(payment.date),
                                        'amount': payment.amount,
                                        'id': payment.id,
                                    }
                                    payments.append(payment_info)
                            
                            # Also check account.move.line for payment entries
                            if not payments:
                                payment_lines = env['account.move.line'].search([
                                    ('move_id', '=', bill.id),
                                    ('reconciled', '=', True)
                                ])
                                
                                for line in payment_lines:
                                    # Find the payment move that reconciled this line
                                    reconciled_lines = env['account.move.line'].search([
                                        ('full_reconcile_id', '=', line.full_reconcile_id.id),
                                        ('move_id', '!=', bill.id)
                                    ])
                                    
                                    for rec_line in reconciled_lines:
                                        payment_move = rec_line.move_id
                                        if payment_move.move_type == 'entry' and payment_move.state == 'posted':
                                            payment_info = {
                                                'name': payment_move.name,
                                                'date': str(payment_move.date),
                                                'amount': abs(rec_line.balance),
                                                'id': payment_move.id,
                                            }
                                            if payment_info not in payments:
                                                payments.append(payment_info)
                        
                        bill_info['payments'] = payments
                        result['vendor_bills'].append(bill_info)
                        result['payments'].extend(payments)
                else:
                    _logger.warning("⚠️ Purchase Order not found for RFQ %s. Migration line: ID=%s, odoo19_rfq_id=%s, in_system_rfq_number=%s", 
                                  rfq_number, 
                                  migration_line.id if migration_line else 'Not found',
                                  migration_line.odoo19_rfq_id.id if migration_line and migration_line.odoo19_rfq_id else 'None',
                                  migration_line.in_system_rfq_number if migration_line else 'None')
                    # Still return bill numbers and IDs from queue list even if PO not found
                    if migration_line:
                        bill_numbers_from_queue = []
                        bill_ids_from_queue = []
                        if migration_line.bills_number:
                            bill_numbers_from_queue = [b.strip() for b in migration_line.bills_number.split(',') if b.strip()]
                        if migration_line.odoo14_bill_ids:
                            bill_ids_from_queue = [b.strip() for b in migration_line.odoo14_bill_ids.split(',') if b.strip()]
                        result['bill_numbers_from_queue'] = bill_numbers_from_queue
                        result['bill_ids_from_queue'] = bill_ids_from_queue
                
                import json
                return request.make_response(
                    json.dumps(result, default=str),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            finally:
                cr.close()
                
        except Exception as e:
            import json
            _logger.error("Error getting RFQ details: %s", str(e), exc_info=True)
            return request.make_response(
                json.dumps({'error': str(e)}),
                headers=[('Content-Type', 'application/json; charset=utf-8')]
            )

    @http.route('/migration/status_rfq', type='http', auth='public', methods=['GET'], csrf=False)
    def get_rfq_status(self, **kwargs):
        """
        Get current RFQ migration status without processing.
        Returns JSON with detailed status.
        
        Usage: /migration/status_rfq?db=your_database_name
        """
        try:
            db = kwargs.get('db')
            
            if not db and hasattr(request, 'httprequest') and request.httprequest:
                from urllib.parse import parse_qs, urlparse
                try:
                    parsed = urlparse(request.httprequest.url)
                    query_params = parse_qs(parsed.query)
                    if 'db' in query_params:
                        db = query_params['db'][0]
                except:
                    pass
            
            if not db:
                import json
                return request.make_response(
                    json.dumps({'error': 'Database not specified. Use: /migration/status_rfq?db=your_database_name'}),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            
            from odoo.api import Environment
            from odoo import sql_db
            try:
                db_conn = sql_db.db_connect(db)
                cr = db_conn.cursor()
            except Exception as reg_error:
                import json
                return request.make_response(
                    json.dumps({'error': f'Database "{db}" not found: {str(reg_error)}'}),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            
            try:
                env = Environment(cr, 1, {})
                
                MigrationRFQ = env['rfq.migration.line']
                
                total_queued = MigrationRFQ.search_count([
                    ('status', '=', 'queued')
                ])
                
                currently_migrating = MigrationRFQ.search([
                    ('status', '=', 'migrating')
                ], limit=1, order='write_date desc')
                
                migrating_rfq = currently_migrating.uploaded_rfq_number if currently_migrating else None
                
                total_migrated = MigrationRFQ.search_count([
                    ('status', '=', 'migrated')
                ])
                
                total_errors = MigrationRFQ.search_count([
                    ('status', '=', 'error')
                ])
                
                import json
                status_data = {
                    'total_queued': total_queued,
                    'migrating_now': migrating_rfq,
                    'total_migrated': total_migrated,
                    'total_errors': total_errors,
                }
                
                return request.make_response(
                    json.dumps(status_data, indent=2),
                    headers=[
                        ('Content-Type', 'application/json; charset=utf-8'),
                    ]
                )
            finally:
                cr.close()
            
        except Exception as e:
            _logger.error("Error in RFQ migration status: %s", str(e), exc_info=True)
            import json
            return request.make_response(
                json.dumps({'error': str(e)}),
                headers=[
                    ('Content-Type', 'application/json; charset=utf-8'),
                ]
            )

    @http.route('/migration/process_one_invoice', type='http', auth='public', methods=['GET'], csrf=False)
    def process_one_invoice(self, **kwargs):
        """
        Process one customer invoice from the queue.
        Can be called repeatedly like a cron job.
        
        Returns simple text response with status.
        
        Usage: /migration/process_one_invoice?db=your_database_name
        """
        _logger.info("=" * 50)
        _logger.info("process_one_invoice ROUTE CALLED!")
        _logger.info("URL: %s", request.httprequest.url if hasattr(request, 'httprequest') and request.httprequest else 'N/A')
        _logger.info("kwargs: %s", kwargs)
        _logger.info("=" * 50)
        try:
            db = kwargs.get('db')
            
            if not db and hasattr(request, 'httprequest') and request.httprequest:
                from urllib.parse import parse_qs, urlparse
                try:
                    parsed = urlparse(request.httprequest.url)
                    query_params = parse_qs(parsed.query)
                    if 'db' in query_params:
                        db = query_params['db'][0]
                except:
                    pass
            
            if not db:
                return request.make_response(
                    'ERROR: Database not specified. Use: /migration/process_one_invoice?db=your_database_name\n',
                    headers=[('Content-Type', 'text/plain; charset=utf-8')]
                )
            
            from odoo.api import Environment
            from odoo import sql_db
            try:
                db_conn = sql_db.db_connect(db)
                cr = db_conn.cursor()
            except Exception as reg_error:
                return request.make_response(
                    f'ERROR: Database "{db}" not found: {str(reg_error)}\n',
                    headers=[('Content-Type', 'text/plain; charset=utf-8')]
                )
            
            try:
                env = Environment(cr, 1, {})
                
                MigrationInvoice = env['customer.invoice.migration.line']
            
                total_queued = MigrationInvoice.search_count([
                    ('status', '=', 'queued')
                ])
                _logger.info("Total queued invoices: %s (status='queued')", total_queued)
                
                # Check for stuck migrations
                from datetime import timedelta
                stuck_threshold = fields.Datetime.now() - timedelta(seconds=30)
                
                all_migrating = MigrationInvoice.search([
                    ('status', '=', 'migrating')
                ])
                
                stuck_count = 0
                for migrating_record in all_migrating:
                    if migrating_record.write_date and migrating_record.write_date < stuck_threshold:
                        stuck_seconds = int((fields.Datetime.now() - migrating_record.write_date).total_seconds())
                        _logger.warning("Found stuck invoice migration: %s (stuck for %s seconds), resetting to error", 
                                      migrating_record.uploaded_invoice_number,
                                      stuck_seconds)
                        migrating_record.write({
                            'status': 'error',
                            'status_message': 'Migration stuck - reset to error',
                            'error_message': f'Migration was stuck in migrating status for {stuck_seconds} seconds. Last update: {migrating_record.write_date}',
                        })
                        stuck_count += 1
                
                if stuck_count > 0:
                    cr.commit()
                    _logger.warning("Reset %s stuck invoice migration(s) to error status", stuck_count)
                
                currently_migrating = MigrationInvoice.search([
                    ('status', '=', 'migrating'),
                    ('write_date', '>=', stuck_threshold)
                ], limit=1, order='write_date desc')
                
                migrating_invoice = 'None'
                
                invoice_to_process = None
                if not currently_migrating:
                    invoice_to_process = MigrationInvoice.search([
                        ('status', '=', 'queued')
                    ], limit=1, order='id asc')
                
                if invoice_to_process and not currently_migrating:
                    try:
                        if invoice_to_process.status != 'queued':
                            migrating_invoice = f"Skipped: {invoice_to_process.status} (not queued)"
                        else:
                            invoice_number = invoice_to_process.uploaded_invoice_number
                            _logger.info("🔄 Starting SYNCHRONOUS migration for invoice %s", invoice_number)
                            
                            invoice_to_process.write({
                                'status': 'pending_migration',
                                'status_message': 'Starting migration...',
                            })
                            cr.commit()
                            migrating_invoice = invoice_number
                            
                            try:
                                existing_invoice = env['account.move'].search([
                                    ('name', '=', invoice_number),
                                    ('move_type', '=', 'out_invoice')
                                ], limit=1)
                                
                                if existing_invoice:
                                    if invoice_to_process.status in ('queued', 'pending_migration'):
                                        _logger.info("Invoice %s already exists in Odoo 19 (ID: %s), updating status to migrated", 
                                                   invoice_number, existing_invoice.id)
                                        invoice_to_process.write({
                                            'status': 'migrated',
                                            'status_message': 'Already migrated (existed in system)',
                                            'odoo19_invoice_id': existing_invoice.id,
                                            'in_system_invoice_number': existing_invoice.name,
                                            'migration_date': fields.Datetime.now(),
                                            'error_message': False,
                                        })
                                        cr.commit()
                                        migrating_invoice = f"{invoice_number} - DONE (already existed)"
                                        _logger.info("✅ Invoice %s marked as migrated (already existed)", invoice_number)
                                    else:
                                        migrating_invoice = f"{invoice_number} - Already migrated"
                                else:
                                    try:
                                        result = invoice_to_process.action_migrate()
                                        cr.commit()
                                        migrating_invoice = f"{invoice_number} - DONE"
                                        _logger.info("✅ Successfully migrated invoice %s", invoice_number)
                                    except Exception as migrate_exception:
                                        error_msg = str(migrate_exception)
                                        _logger.error("❌ Error migrating invoice %s: %s", invoice_number, error_msg, exc_info=True)
                                        _log_failed_invoice_migration(invoice_number, error_msg)
                                        migrating_invoice = f"{invoice_number} - ERROR: {error_msg[:100]}"
                            except Exception as e:
                                error_msg = str(e)
                                _logger.error("❌ Error processing invoice %s: %s", invoice_number, error_msg, exc_info=True)
                                _log_failed_invoice_migration(invoice_number, error_msg)
                                migrating_invoice = f"{invoice_number} - ERROR: {error_msg[:100]}"
                    except Exception as e:
                        _logger.error("❌ Error in invoice migration process: %s", str(e), exc_info=True)
                        migrating_invoice = f"ERROR: {str(e)[:100]}"
                elif currently_migrating:
                    migrating_invoice = f"{currently_migrating.uploaded_invoice_number} - in progress"
                
                total_migrated = MigrationInvoice.search_count([
                    ('status', '=', 'migrated')
                ])
                
                total_errors = MigrationInvoice.search_count([
                    ('status', '=', 'error')
                ])
                
                response_text = f"""Migrating Now: {migrating_invoice}
Total Queued: {total_queued} (status='queued')
Total Migrated: {total_migrated}
Total Errors: {total_errors}
"""
                
                return request.make_response(
                    response_text,
                    headers=[('Content-Type', 'text/plain; charset=utf-8')]
                )
            finally:
                cr.close()
            
        except Exception as e:
            _logger.error("Error in invoice migration process: %s", str(e), exc_info=True)
            return request.make_response(
                f'ERROR: {str(e)}\n',
                headers=[('Content-Type', 'text/plain; charset=utf-8')]
            )

    @http.route('/migration/status_invoice', type='http', auth='public', methods=['GET'], csrf=False)
    def get_invoice_status(self, **kwargs):
        """
        Get current customer invoice migration status without processing.
        Returns JSON with detailed status.
        
        Usage: /migration/status_invoice?db=your_database_name
        """
        try:
            db = kwargs.get('db')
            
            if not db and hasattr(request, 'httprequest') and request.httprequest:
                from urllib.parse import parse_qs, urlparse
                try:
                    parsed = urlparse(request.httprequest.url)
                    query_params = parse_qs(parsed.query)
                    if 'db' in query_params:
                        db = query_params['db'][0]
                except:
                    pass
            
            if not db:
                import json
                return request.make_response(
                    json.dumps({'error': 'Database not specified. Use: /migration/status_invoice?db=your_database_name'}),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            
            from odoo.api import Environment
            from odoo import sql_db
            try:
                db_conn = sql_db.db_connect(db)
                cr = db_conn.cursor()
            except Exception as reg_error:
                import json
                return request.make_response(
                    json.dumps({'error': f'Database "{db}" not found: {str(reg_error)}'}),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            
            try:
                env = Environment(cr, 1, {})
                
                MigrationInvoice = env['customer.invoice.migration.line']
                
                total_queued = MigrationInvoice.search_count([
                    ('status', '=', 'queued')
                ])
                
                currently_migrating = MigrationInvoice.search([
                    ('status', '=', 'migrating')
                ], limit=1, order='write_date desc')
                
                migrating_invoice = currently_migrating.uploaded_invoice_number if currently_migrating else None
                
                total_migrated = MigrationInvoice.search_count([
                    ('status', '=', 'migrated')
                ])
                
                total_errors = MigrationInvoice.search_count([
                    ('status', '=', 'error')
                ])
                
                import json
                status_data = {
                    'total_queued': total_queued,
                    'migrating_now': migrating_invoice,
                    'total_migrated': total_migrated,
                    'total_errors': total_errors,
                }
                
                return request.make_response(
                    json.dumps(status_data, indent=2),
                    headers=[
                        ('Content-Type', 'application/json; charset=utf-8'),
                    ]
                )
            finally:
                cr.close()
            
        except Exception as e:
            _logger.error("Error in invoice migration status: %s", str(e), exc_info=True)
            import json
            return request.make_response(
                json.dumps({'error': str(e)}),
                headers=[
                    ('Content-Type', 'application/json; charset=utf-8'),
                ]
            )

    @http.route('/migration/process_one_vendor_bill', type='http', auth='public', methods=['GET'], csrf=False)
    def process_one_vendor_bill(self, **kwargs):
        """
        Process one vendor bill from the queue.
        Can be called repeatedly like a cron job.
        
        Returns simple text response with status.
        
        Usage: /migration/process_one_vendor_bill?db=your_database_name
        """
        _logger.info("=" * 50)
        _logger.info("process_one_vendor_bill ROUTE CALLED!")
        _logger.info("URL: %s", request.httprequest.url if hasattr(request, 'httprequest') and request.httprequest else 'N/A')
        _logger.info("kwargs: %s", kwargs)
        _logger.info("=" * 50)
        try:
            db = kwargs.get('db')
            
            if not db and hasattr(request, 'httprequest') and request.httprequest:
                from urllib.parse import parse_qs, urlparse
                try:
                    parsed = urlparse(request.httprequest.url)
                    query_params = parse_qs(parsed.query)
                    if 'db' in query_params:
                        db = query_params['db'][0]
                except:
                    pass
            
            if not db:
                return request.make_response(
                    'ERROR: Database not specified. Use: /migration/process_one_vendor_bill?db=your_database_name\n',
                    headers=[('Content-Type', 'text/plain; charset=utf-8')]
                )
            
            from odoo.api import Environment
            from odoo import sql_db
            try:
                db_conn = sql_db.db_connect(db)
                cr = db_conn.cursor()
            except Exception as reg_error:
                return request.make_response(
                    f'ERROR: Database "{db}" not found: {str(reg_error)}\n',
                    headers=[('Content-Type', 'text/plain; charset=utf-8')]
                )
            
            try:
                env = Environment(cr, 1, {})
                
                MigrationBill = env['vendor.bill.migration.line']
            
                total_queued = MigrationBill.search_count([
                    ('status', '=', 'queued')
                ])
                _logger.info("Total queued vendor bills: %s (status='queued')", total_queued)
                
                # Check for stuck migrations (increased to 60 seconds to allow for complex migrations with many lines)
                from datetime import timedelta
                stuck_threshold = fields.Datetime.now() - timedelta(seconds=60)
                
                all_migrating = MigrationBill.search([
                    ('status', '=', 'migrating')
                ])
                
                stuck_count = 0
                for migrating_record in all_migrating:
                    if migrating_record.write_date and migrating_record.write_date < stuck_threshold:
                        stuck_seconds = int((fields.Datetime.now() - migrating_record.write_date).total_seconds())
                        _logger.warning("Found stuck vendor bill migration: %s (stuck for %s seconds), resetting to error", 
                                      migrating_record.uploaded_bill_number,
                                      stuck_seconds)
                        try:
                            migrating_record.write({
                                'status': 'error',
                                'status_message': 'Migration stuck - reset to error',
                                'error_message': f'Migration was stuck in migrating status for {stuck_seconds} seconds. Last update: {migrating_record.write_date}',
                            })
                            stuck_count += 1
                        except Exception as stuck_error:
                            _logger.error("Error resetting stuck migration %s: %s", migrating_record.uploaded_bill_number, str(stuck_error))
                            try:
                                cr.rollback()
                            except:
                                pass
                
                if stuck_count > 0:
                    try:
                        cr.commit()
                        _logger.warning("Reset %s stuck vendor bill migration(s) to error status", stuck_count)
                    except Exception as commit_error:
                        _logger.error("Error committing stuck migration reset: %s", str(commit_error))
                        try:
                            cr.rollback()
                        except:
                            pass
                
                # Find currently migrating (recent ones, not stuck - within last 60 seconds)
                currently_migrating = MigrationBill.search([
                    ('status', '=', 'migrating'),
                    ('write_date', '>=', stuck_threshold)
                ], limit=1, order='write_date desc')
                
                migrating_bill = 'None'
                migrating_bill_details = None
                
                bill_to_process = None
                if not currently_migrating:
                    # Use SELECT FOR UPDATE SKIP LOCKED to avoid concurrent update conflicts
                    try:
                        cr.execute("""
                            SELECT id FROM vendor_bill_migration_line 
                            WHERE status = 'queued' 
                            ORDER BY id ASC 
                            LIMIT 1 
                            FOR UPDATE SKIP LOCKED
                        """)
                        result = cr.fetchone()
                        if result:
                            bill_id = result[0]
                            bill_to_process = MigrationBill.browse(bill_id)
                    except Exception as lock_error:
                        _logger.warning("Error using SELECT FOR UPDATE SKIP LOCKED: %s, falling back to regular search", str(lock_error))
                        bill_to_process = MigrationBill.search([
                            ('status', '=', 'queued')
                        ], limit=1, order='id asc')
                
                if bill_to_process and not currently_migrating:
                    try:
                        if bill_to_process.status != 'queued':
                            migrating_bill = f"Skipped: {bill_to_process.status} (not queued)"
                        else:
                            bill_number = bill_to_process.uploaded_bill_number
                            partner_name = bill_to_process.bill_partner_name or 'N/A'
                            _logger.info("🔄 Starting SYNCHRONOUS migration for vendor bill %s", bill_number)
                            
                            # Get bill amount from Odoo 14 if config available
                            bill_amount = 0.0
                            if bill_to_process.config_id:
                                try:
                                    from ..models.odoo14_api_client import Odoo14APIClient
                                    client = Odoo14APIClient(
                                        url=bill_to_process.config_id.odoo14_url,
                                        db=bill_to_process.config_id.odoo14_database,
                                        username=bill_to_process.config_id.odoo14_username,
                                        password=bill_to_process.config_id.odoo14_password
                                    )
                                    if client.authenticate():
                                        bills = client.search_read(
                                            'account.move',
                                            [('name', '=', bill_number), ('move_type', '=', 'in_invoice')],
                                            ['amount_total', 'partner_id'],
                                            limit=1
                                        )
                                        if bills:
                                            bill_amount = bills[0].get('amount_total', 0.0)
                                            # Get partner name if not set
                                            if not partner_name or partner_name == 'N/A':
                                                partner_id = bills[0].get('partner_id')
                                                if partner_id and isinstance(partner_id, (list, tuple)) and len(partner_id) > 1:
                                                    partner_name = partner_id[1]
                                except:
                                    pass
                            
                            # Update status with retry logic for serialization errors
                            max_retries = 3
                            updated = False
                            for retry in range(max_retries):
                                try:
                                    bill_to_process.write({
                                        'status': 'pending_migration',
                                        'status_message': 'Starting migration...',
                                    })
                                    cr.commit()
                                    updated = True
                                    migrating_bill = bill_number
                                    break
                                except Exception as write_error:
                                    error_msg = str(write_error).lower()
                                    is_serialization_error = (
                                        'could not serialize' in error_msg or
                                        'concurrent update' in error_msg or
                                        'serialization failure' in error_msg
                                    )
                                    
                                    if is_serialization_error and retry < max_retries - 1:
                                        import time
                                        delay = 0.1 * (2 ** retry)  # Exponential backoff
                                        _logger.warning("Serialization error updating status (retry %s/%s), waiting %s seconds: %s", 
                                                      retry + 1, max_retries, delay, str(write_error))
                                        try:
                                            cr.rollback()
                                        except:
                                            pass
                                        time.sleep(delay)
                                        # Refresh record
                                        bill_to_process.invalidate_recordset(['status'])
                                        # Check if already being processed
                                        if bill_to_process.status in ('migrating', 'pending_migration'):
                                            _logger.info("Bill %s is already being processed (status: %s), skipping", 
                                                       bill_number, bill_to_process.status)
                                            migrating_bill = f"{bill_number} - Already processing"
                                            updated = True
                                            break
                                    else:
                                        _logger.error("Error updating bill status to pending_migration: %s", str(write_error))
                                        try:
                                            cr.rollback()
                                        except:
                                            pass
                                        if retry == max_retries - 1:
                                            # Last retry failed, try to continue anyway
                                            migrating_bill = bill_number
                                            updated = True
                            
                            if not updated:
                                migrating_bill = bill_number
                            
                            # Include bill details in response
                            # State: Excel status takes priority, payment_state always "not_paid"
                            state_value = bill_to_process.excel_status or bill_to_process.odoo14_state or 'N/A'
                            total_items_odoo14 = 0
                            total_items_odoo19 = 0
                            products_odoo14 = 0
                            products_odoo19 = 0
                            migrating_bill_details = {
                                'bill_number': bill_number,
                                'partner_name': partner_name,
                                'amount_total': bill_amount,
                                'state': state_value,
                                'payment_state': 'not_paid',  # Always "not_paid"
                                'total_items_odoo14': total_items_odoo14,
                                'total_items_odoo19': total_items_odoo19,
                                'products_odoo14': products_odoo14,
                                'products_odoo19': products_odoo19,
                            }
                            
                            try:
                                existing_bill = env['account.move'].search([
                                    ('name', '=', bill_number),
                                    ('move_type', '=', 'in_invoice')
                                ], limit=1)
                                
                                if existing_bill:
                                    # Count products in Odoo 19 bill (lines with product_id)
                                    if existing_bill.invoice_line_ids:
                                        total_items_odoo19 = len(existing_bill.invoice_line_ids)
                                        products_odoo19 = len(existing_bill.invoice_line_ids.filtered(lambda l: l.product_id))
                                        migrating_bill_details['total_items_odoo19'] = total_items_odoo19
                                        migrating_bill_details['products_odoo19'] = products_odoo19
                                elif bill_to_process.odoo19_bill_id:
                                    # Bill is already migrated, use odoo19_bill_id to count products
                                    odoo19_bill = bill_to_process.odoo19_bill_id
                                    if odoo19_bill.invoice_line_ids:
                                        total_items_odoo19 = len(odoo19_bill.invoice_line_ids)
                                        products_odoo19 = len(odoo19_bill.invoice_line_ids.filtered(lambda l: l.product_id))
                                        migrating_bill_details['total_items_odoo19'] = total_items_odoo19
                                        migrating_bill_details['products_odoo19'] = products_odoo19
                                        migrating_bill_details['amount_total'] = odoo19_bill.amount_total or 0.0
                                        if odoo19_bill.partner_id:
                                            migrating_bill_details['partner_name'] = odoo19_bill.partner_id.name or partner_name
                                        migrating_bill_details['state'] = bill_to_process.excel_status or odoo19_bill.state or bill_to_process.odoo14_state or 'N/A'
                                
                                if existing_bill:
                                    if bill_to_process.status in ('queued', 'pending_migration'):
                                        _logger.info("Vendor bill %s already exists in Odoo 19 (ID: %s), updating status to migrated", 
                                                   bill_number, existing_bill.id)
                                        try:
                                            bill_to_process.write({
                                                'status': 'migrated',
                                                'status_message': 'Already migrated (existed in system)',
                                                'odoo19_bill_id': existing_bill.id,
                                                'in_system_bill_number': existing_bill.name,
                                                'migration_date': fields.Datetime.now(),
                                                'error_message': False,
                                            })
                                            cr.commit()
                                            migrating_bill = f"{bill_number} - DONE (already existed)"
                                            # Update bill details with existing bill info
                                            migrating_bill_details['amount_total'] = existing_bill.amount_total or 0.0
                                            if existing_bill.partner_id:
                                                migrating_bill_details['partner_name'] = existing_bill.partner_id.name or partner_name
                                            # Update state from existing bill (Excel status takes priority), payment_state always "not_paid"
                                            migrating_bill_details['state'] = bill_to_process.excel_status or existing_bill.state or bill_to_process.odoo14_state or 'N/A'
                                            migrating_bill_details['payment_state'] = 'not_paid'  # Always "not_paid"
                                            _logger.info("✅ Vendor bill %s marked as migrated (already existed)", bill_number)
                                        except Exception as update_error:
                                            _logger.error("Error updating bill status to migrated: %s", str(update_error))
                                            try:
                                                cr.rollback()
                                            except:
                                                pass
                                            migrating_bill = f"{bill_number} - DONE (already existed)"
                                    else:
                                        migrating_bill = f"{bill_number} - DONE"
                                    
                                    # Fetch Odoo 14 products for already-migrated bills
                                    if bill_to_process.config_id:
                                        try:
                                            from ..models.odoo14_api_client import Odoo14APIClient
                                            client = Odoo14APIClient(
                                                url=bill_to_process.config_id.odoo14_url,
                                                db=bill_to_process.config_id.odoo14_database,
                                                username=bill_to_process.config_id.odoo14_username,
                                                password=bill_to_process.config_id.odoo14_password
                                            )
                                            if client.authenticate():
                                                bills = client.search_read(
                                                    'account.move',
                                                    [('name', '=', bill_number), ('move_type', '=', 'in_invoice')],
                                                    ['invoice_line_ids'],
                                                    limit=1
                                                )
                                                if bills:
                                                    invoice_line_ids = bills[0].get('invoice_line_ids', [])
                                                    if invoice_line_ids:
                                                        if isinstance(invoice_line_ids, (list, tuple)):
                                                            total_items_odoo14 = len([lid for lid in invoice_line_ids if isinstance(lid, int) or (isinstance(lid, (list, tuple)) and len(lid) > 0)])
                                                        else:
                                                            total_items_odoo14 = 1 if invoice_line_ids else 0
                                                        
                                                        # Count products from Odoo 14
                                                        try:
                                                            line_ids = [lid[0] if isinstance(lid, (list, tuple)) and len(lid) > 0 else lid for lid in invoice_line_ids if lid]
                                                            if line_ids:
                                                                lines = client.search_read(
                                                                    'account.move.line',
                                                                    [('id', 'in', line_ids), ('move_id', '=', bills[0]['id'])],
                                                                    ['product_id'],
                                                                    limit=1000
                                                                )
                                                                if lines:
                                                                    products_odoo14 = len([l for l in lines if l.get('product_id')])
                                                                    migrating_bill_details['products_odoo14'] = products_odoo14
                                                                    migrating_bill_details['total_items_odoo14'] = total_items_odoo14
                                                        except Exception as product_count_error:
                                                            _logger.debug("Could not count products from Odoo 14 for migrated bill: %s", str(product_count_error))
                                        except Exception as odoo14_error:
                                            _logger.debug("Could not fetch Odoo 14 products for migrated bill: %s", str(odoo14_error))
                                else:
                                    try:
                                        result = bill_to_process.action_migrate()
                                        try:
                                            cr.commit()
                                        except Exception as commit_error:
                                            _logger.warning("Error committing migration result: %s", str(commit_error))
                                            try:
                                                cr.rollback()
                                            except:
                                                pass
                                        migrating_bill = f"{bill_number} - DONE"
                                        # Update bill details if bill was created
                                        try:
                                            # Refresh bill_to_process to get updated data
                                            bill_to_process.invalidate_recordset(['odoo19_bill_id', 'odoo14_state', 'odoo14_payment_state'])
                                            if bill_to_process.odoo19_bill_id:
                                                migrating_bill_details['amount_total'] = bill_to_process.odoo19_bill_id.amount_total or bill_amount
                                                if bill_to_process.odoo19_bill_id.partner_id:
                                                    migrating_bill_details['partner_name'] = bill_to_process.odoo19_bill_id.partner_id.name or partner_name
                                                # Update state from migrated bill (Excel status takes priority), payment_state always "not_paid"
                                                migrating_bill_details['state'] = bill_to_process.excel_status or bill_to_process.odoo19_bill_id.state or bill_to_process.odoo14_state or 'N/A'
                                                migrating_bill_details['payment_state'] = 'not_paid'  # Always "not_paid"
                                                
                                                # Count products in Odoo 19 bill
                                                if bill_to_process.odoo19_bill_id.invoice_line_ids:
                                                    total_items_odoo19 = len(bill_to_process.odoo19_bill_id.invoice_line_ids)
                                                    products_odoo19 = len(bill_to_process.odoo19_bill_id.invoice_line_ids.filtered(lambda l: l.product_id))
                                                    migrating_bill_details['total_items_odoo19'] = total_items_odoo19
                                                    migrating_bill_details['products_odoo19'] = products_odoo19
                                                
                                                # Fetch Odoo 14 products
                                                if bill_to_process.config_id:
                                                    try:
                                                        from ..models.odoo14_api_client import Odoo14APIClient
                                                        client = Odoo14APIClient(
                                                            url=bill_to_process.config_id.odoo14_url,
                                                            db=bill_to_process.config_id.odoo14_database,
                                                            username=bill_to_process.config_id.odoo14_username,
                                                            password=bill_to_process.config_id.odoo14_password
                                                        )
                                                        if client.authenticate():
                                                            bills = client.search_read(
                                                                'account.move',
                                                                [('name', '=', bill_number), ('move_type', '=', 'in_invoice')],
                                                                ['invoice_line_ids'],
                                                                limit=1
                                                            )
                                                            if bills:
                                                                invoice_line_ids = bills[0].get('invoice_line_ids', [])
                                                                if invoice_line_ids:
                                                                    if isinstance(invoice_line_ids, (list, tuple)):
                                                                        total_items_odoo14 = len([lid for lid in invoice_line_ids if isinstance(lid, int) or (isinstance(lid, (list, tuple)) and len(lid) > 0)])
                                                                    else:
                                                                        total_items_odoo14 = 1 if invoice_line_ids else 0
                                                                    
                                                                    # Count products from Odoo 14
                                                                    try:
                                                                        line_ids = [lid[0] if isinstance(lid, (list, tuple)) and len(lid) > 0 else lid for lid in invoice_line_ids if lid]
                                                                        if line_ids:
                                                                            lines = client.search_read(
                                                                                'account.move.line',
                                                                                [('id', 'in', line_ids), ('move_id', '=', bills[0]['id'])],
                                                                                ['product_id'],
                                                                                limit=1000
                                                                            )
                                                                            if lines:
                                                                                products_odoo14 = len([l for l in lines if l.get('product_id')])
                                                                                migrating_bill_details['products_odoo14'] = products_odoo14
                                                                                migrating_bill_details['total_items_odoo14'] = total_items_odoo14
                                                                    except Exception as product_count_error:
                                                                        _logger.debug("Could not count products from Odoo 14 for newly migrated bill: %s", str(product_count_error))
                                                    except Exception as odoo14_error:
                                                        _logger.debug("Could not fetch Odoo 14 products for newly migrated bill: %s", str(odoo14_error))
                                            else:
                                                # Use values from migration line if bill not yet linked
                                                migrating_bill_details['state'] = bill_to_process.excel_status or bill_to_process.odoo14_state or 'N/A'
                                                migrating_bill_details['payment_state'] = 'not_paid'  # Always "not_paid"
                                        except:
                                            pass
                                        _logger.info("✅ Successfully migrated vendor bill %s", bill_number)
                                    except Exception as migrate_exception:
                                        error_msg = str(migrate_exception)
                                        _logger.error("❌ Error migrating vendor bill %s: %s", bill_number, error_msg, exc_info=True)
                                        _log_failed_vendor_bill_migration(bill_number, error_msg)
                                        try:
                                            cr.rollback()
                                        except:
                                            pass
                                        # Try to update status to error
                                        try:
                                            bill_to_process.write({
                                                'status': 'error',
                                                'status_message': 'Migration failed',
                                                'error_message': error_msg[:500],
                                            })
                                            cr.commit()
                                        except:
                                            try:
                                                cr.rollback()
                                            except:
                                                pass
                                        migrating_bill = f"{bill_number} - ERROR: {error_msg[:100]}"
                            except Exception as e:
                                error_msg = str(e)
                                _logger.error("❌ Error processing vendor bill %s: %s", bill_number, error_msg, exc_info=True)
                                _log_failed_vendor_bill_migration(bill_number, error_msg)
                                try:
                                    cr.rollback()
                                except:
                                    pass
                                migrating_bill = f"{bill_number} - ERROR: {error_msg[:100]}"
                    except Exception as e:
                        _logger.error("❌ Error in vendor bill migration process: %s", str(e), exc_info=True)
                        migrating_bill = f"ERROR: {str(e)[:100]}"
                elif currently_migrating:
                    migrating_bill = f"{currently_migrating.uploaded_bill_number} - in progress"
                    # Get bill details for currently migrating bill
                    partner_name = currently_migrating.bill_partner_name or 'N/A'
                    bill_amount = 0.0
                    state_value = currently_migrating.excel_status or currently_migrating.odoo14_state or 'N/A'
                    total_items_odoo14 = 0
                    total_items_odoo19 = 0
                    products_odoo14 = 0
                    products_odoo19 = 0
                    
                    if currently_migrating.odoo19_bill_id:
                        bill_amount = currently_migrating.odoo19_bill_id.amount_total or 0.0
                        # Update state from Odoo 19 bill (Excel status still takes priority)
                        if not currently_migrating.excel_status:
                            state_value = currently_migrating.odoo19_bill_id.state or currently_migrating.odoo14_state or 'N/A'
                        # Count items in Odoo 19 bill
                        total_items_odoo19 = len(currently_migrating.odoo19_bill_id.invoice_line_ids) if currently_migrating.odoo19_bill_id.invoice_line_ids else 0
                        # Count products in Odoo 19 bill (lines with product_id)
                        if currently_migrating.odoo19_bill_id.invoice_line_ids:
                            products_odoo19 = len(currently_migrating.odoo19_bill_id.invoice_line_ids.filtered(lambda l: l.product_id))
                    
                    # Get total items from Odoo 14 (before migration)
                    if currently_migrating.config_id:
                        try:
                            from ..models.odoo14_api_client import Odoo14APIClient
                            client = Odoo14APIClient(
                                url=currently_migrating.config_id.odoo14_url,
                                db=currently_migrating.config_id.odoo14_database,
                                username=currently_migrating.config_id.odoo14_username,
                                password=currently_migrating.config_id.odoo14_password
                            )
                            if client.authenticate():
                                bills = client.search_read(
                                    'account.move',
                                    [('name', '=', currently_migrating.uploaded_bill_number), ('move_type', '=', 'in_invoice')],
                                    ['amount_total', 'state', 'invoice_line_ids'],
                                    limit=1
                                )
                                if bills:
                                    bill_amount = bills[0].get('amount_total', 0.0)
                                    # Update state from Odoo 14 if Excel status not available
                                    if not currently_migrating.excel_status and bills[0].get('state'):
                                        state_value = bills[0].get('state')
                                    # Count items from Odoo 14
                                    invoice_line_ids = bills[0].get('invoice_line_ids', [])
                                    if invoice_line_ids:
                                        if isinstance(invoice_line_ids, (list, tuple)):
                                            total_items_odoo14 = len([lid for lid in invoice_line_ids if isinstance(lid, int) or (isinstance(lid, (list, tuple)) and len(lid) > 0)])
                                        else:
                                            total_items_odoo14 = 1 if invoice_line_ids else 0
                                    
                                    # Count products from Odoo 14 (fetch lines with product_id)
                                    if invoice_line_ids:
                                        try:
                                            line_ids = [lid[0] if isinstance(lid, (list, tuple)) and len(lid) > 0 else lid for lid in invoice_line_ids if lid]
                                            if line_ids:
                                                lines = client.search_read(
                                                    'account.move.line',
                                                    [('id', 'in', line_ids), ('move_id', '=', bills[0]['id'])],
                                                    ['product_id'],
                                                    limit=1000
                                                )
                                                if lines:
                                                    products_odoo14 = len([l for l in lines if l.get('product_id')])
                                        except Exception as product_count_error:
                                            _logger.debug("Could not count products from Odoo 14: %s", str(product_count_error))
                        except Exception as odoo14_error:
                            _logger.warning("Could not fetch Odoo 14 bill details: %s", str(odoo14_error))
                    
                    # State: Excel status takes priority, payment_state always "not_paid"
                    migrating_bill_details = {
                        'bill_number': currently_migrating.uploaded_bill_number,
                        'partner_name': partner_name,
                        'amount_total': bill_amount,
                        'state': state_value,
                        'payment_state': 'not_paid',  # Always "not_paid"
                        'total_items_odoo14': total_items_odoo14,
                        'total_items_odoo19': total_items_odoo19,
                        'products_odoo14': products_odoo14,
                        'products_odoo19': products_odoo19,
                    }
                
                # Ensure transaction is clean before counting
                # Rollback any failed operations to reset transaction state
                try:
                    cr.rollback()
                except Exception as rollback_error:
                    _logger.debug("Rollback (may be normal): %s", str(rollback_error))
                
                # Get counts with error handling to avoid transaction errors
                # Use raw SQL as fallback if ORM fails due to transaction state
                try:
                    total_migrated = MigrationBill.search_count([
                        ('status', '=', 'migrated')
                    ])
                except Exception as count_error:
                    _logger.warning("Error counting migrated bills with ORM: %s", str(count_error))
                    try:
                        cr.rollback()
                        # Try with raw SQL as fallback
                        cr.execute("""
                            SELECT COUNT(*) 
                            FROM vendor_bill_migration_line 
                            WHERE status = 'migrated'
                        """)
                        total_migrated = cr.fetchone()[0] if cr.rowcount > 0 else 0
                    except Exception as sql_error:
                        _logger.warning("Error counting migrated bills with SQL: %s", str(sql_error))
                        total_migrated = 0
                
                try:
                    total_errors = MigrationBill.search_count([
                        ('status', '=', 'error')
                    ])
                except Exception as count_error:
                    _logger.warning("Error counting error bills with ORM: %s", str(count_error))
                    try:
                        cr.rollback()
                        # Try with raw SQL as fallback
                        cr.execute("""
                            SELECT COUNT(*) 
                            FROM vendor_bill_migration_line 
                            WHERE status = 'error'
                        """)
                        total_errors = cr.fetchone()[0] if cr.rowcount > 0 else 0
                    except Exception as sql_error:
                        _logger.warning("Error counting error bills with SQL: %s", str(sql_error))
                        total_errors = 0
                
                # Get payment information if bill exists in Odoo 19
                payment_count = 0
                if migrating_bill_details:
                    bill_number = migrating_bill_details.get('bill_number', '')
                    if bill_number:
                        try:
                            existing_bill = env['account.move'].search([
                                ('name', '=', bill_number),
                                ('move_type', '=', 'in_invoice')
                            ], limit=1)
                            
                            if existing_bill:
                                # Count payments linked to this bill
                                if 'account.payment' in env.registry:
                                    # Try to find payments via reconciled_invoice_ids (many2many field)
                                    try:
                                        payments = env['account.payment'].search([
                                            ('state', '=', 'posted'),
                                            ('reconciled_invoice_ids', 'in', existing_bill.id)
                                        ])
                                        payment_count = len(payments)
                                    except:
                                        payment_count = 0
                                    
                                    if not payment_count:
                                        # Also check via reconciliation on account.move.line
                                        try:
                                            bill_lines = existing_bill.line_ids.filtered(lambda l: 
                                                hasattr(l.account_id, 'account_type') and 
                                                l.account_id.account_type == 'liability_payable' and 
                                                l.reconciled)
                                            if bill_lines:
                                                # Count unique reconciliations
                                                reconcile_ids = bill_lines.mapped('full_reconcile_id')
                                                payment_count = len(reconcile_ids.filtered(lambda r: r))
                                        except:
                                            pass
                        except:
                            pass
                
                # Build response with bill details if available
                bill_details_text = ""
                if migrating_bill_details:
                    payment_info = ""
                    if payment_count > 0:
                        payment_info = f"Payments Linked: {payment_count}"
                    
                    total_items_odoo14 = migrating_bill_details.get('total_items_odoo14', 0)
                    total_items_odoo19 = migrating_bill_details.get('total_items_odoo19', 0)
                    products_odoo14 = migrating_bill_details.get('products_odoo14', 0)
                    products_odoo19 = migrating_bill_details.get('products_odoo19', 0)
                    items_info = ""
                    if total_items_odoo14 > 0:
                        items_info = f"Total Items (Odoo 14): {total_items_odoo14}"
                    if total_items_odoo19 > 0:
                        if items_info:
                            items_info += f"\nTotal Items Migrated: {total_items_odoo19}"
                        else:
                            items_info = f"Total Items Migrated: {total_items_odoo19}"
                    if products_odoo14 > 0:
                        if items_info:
                            items_info += f"\nProducts (Odoo 14): {products_odoo14}"
                        else:
                            items_info = f"Products (Odoo 14): {products_odoo14}"
                    if products_odoo19 > 0:
                        if items_info:
                            items_info += f"\nProducts Migrated: {products_odoo19}"
                        else:
                            items_info = f"Products Migrated: {products_odoo19}"
                    
                    bill_details_text = f"""
Migrating Vendor Bill details:
Bill Number: {migrating_bill_details.get('bill_number', 'N/A')}
Vendor: {migrating_bill_details.get('partner_name', 'N/A')}
Total Bill Amount: {migrating_bill_details.get('amount_total', 0.0):,.2f}
{items_info}
Status (Posted/Draft): {migrating_bill_details.get('state', 'N/A')}
Payment Status: {migrating_bill_details.get('payment_state', 'N/A')}
{payment_info}
"""
                
                response_text = f"""Migrating Now: {migrating_bill}{bill_details_text}
Total Queued: {total_queued} (status='queued')
Total Migrated: {total_migrated}
Total Errors: {total_errors}
"""
                
                return request.make_response(
                    response_text,
                    headers=[('Content-Type', 'text/plain; charset=utf-8')]
                )
            finally:
                cr.close()
            
        except Exception as e:
            _logger.error("Error in vendor bill migration process: %s", str(e), exc_info=True)
            return request.make_response(
                f'ERROR: {str(e)}\n',
                headers=[('Content-Type', 'text/plain; charset=utf-8')]
            )

    @http.route('/migration/status_vendor_bill', type='http', auth='public', methods=['GET'], csrf=False)
    def get_vendor_bill_status(self, **kwargs):
        """
        Get current vendor bill migration status without processing.
        Returns JSON with detailed status.
        
        Usage: /migration/status_vendor_bill?db=your_database_name
        """
        try:
            db = kwargs.get('db')
            
            if not db and hasattr(request, 'httprequest') and request.httprequest:
                from urllib.parse import parse_qs, urlparse
                try:
                    parsed = urlparse(request.httprequest.url)
                    query_params = parse_qs(parsed.query)
                    if 'db' in query_params:
                        db = query_params['db'][0]
                except:
                    pass
            
            if not db:
                import json
                return request.make_response(
                    json.dumps({'error': 'Database not specified. Use: /migration/status_vendor_bill?db=your_database_name'}),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            
            from odoo.api import Environment
            from odoo import sql_db
            try:
                db_conn = sql_db.db_connect(db)
                cr = db_conn.cursor()
            except Exception as reg_error:
                import json
                return request.make_response(
                    json.dumps({'error': f'Database "{db}" not found: {str(reg_error)}'}),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            
            try:
                env = Environment(cr, 1, {})
                
                MigrationBill = env['vendor.bill.migration.line']
                
                # Get counts with error handling
                try:
                    total_queued = MigrationBill.search_count([
                        ('status', '=', 'queued')
                    ])
                except Exception as count_error:
                    _logger.warning("Error counting queued bills: %s", str(count_error))
                    try:
                        cr.rollback()
                        cr.execute("SELECT COUNT(*) FROM vendor_bill_migration_line WHERE status = 'queued'")
                        total_queued = cr.fetchone()[0] if cr.rowcount > 0 else 0
                    except:
                        total_queued = 0
                
                try:
                    currently_migrating = MigrationBill.search([
                        ('status', '=', 'migrating')
                    ], limit=1, order='write_date desc')
                except Exception as search_error:
                    _logger.warning("Error searching migrating bills: %s", str(search_error))
                    try:
                        cr.rollback()
                        currently_migrating = MigrationBill.browse([])
                    except:
                        currently_migrating = MigrationBill.browse([])
                
                migrating_bill = currently_migrating.uploaded_bill_number if currently_migrating else None
                migrating_bill_details = None
                
                # Get bill details if currently migrating
                if currently_migrating:
                    bill_details = {
                        'bill_number': currently_migrating.uploaded_bill_number,
                        'partner_name': currently_migrating.bill_partner_name or 'N/A',
                        'amount_total': 0.0,
                        'state': currently_migrating.excel_status or currently_migrating.odoo14_state or 'N/A',  # Excel status takes priority
                        'payment_state': 'not_paid',  # Always "not_paid"
                    }
                    
                    # Try to get amount from Odoo 14 or Odoo 19
                    if currently_migrating.odoo19_bill_id:
                        bill_details['amount_total'] = currently_migrating.odoo19_bill_id.amount_total or 0.0
                        # Update state from Excel status (priority) or Odoo 19 bill, payment_state always "not_paid"
                        bill_details['state'] = currently_migrating.excel_status or currently_migrating.odoo19_bill_id.state or bill_details.get('state', 'N/A')
                        bill_details['payment_state'] = 'not_paid'  # Always "not_paid"
                    elif currently_migrating.config_id:
                        try:
                            from ..models.odoo14_api_client import Odoo14APIClient
                            client = Odoo14APIClient(
                                url=currently_migrating.config_id.odoo14_url,
                                db=currently_migrating.config_id.odoo14_database,
                                username=currently_migrating.config_id.odoo14_username,
                                password=currently_migrating.config_id.odoo14_password
                            )
                            if client.authenticate():
                                bills = client.search_read(
                                    'account.move',
                                    [('name', '=', currently_migrating.uploaded_bill_number), ('move_type', '=', 'in_invoice')],
                                    ['amount_total', 'state', 'payment_state'],
                                    limit=1
                                )
                                if bills:
                                    bill_details['amount_total'] = bills[0].get('amount_total', 0.0)
                                    # State: Excel status takes priority over Odoo 14, payment_state always "not_paid"
                                    if not bill_details.get('state') or bill_details.get('state') == 'N/A':
                                        if bills[0].get('state'):
                                            bill_details['state'] = bills[0].get('state')
                                    bill_details['payment_state'] = 'not_paid'  # Always "not_paid"
                        except:
                            pass
                    
                    migrating_bill_details = bill_details
                
                try:
                    total_migrated = MigrationBill.search_count([
                        ('status', '=', 'migrated')
                    ])
                except Exception as count_error:
                    _logger.warning("Error counting migrated bills: %s", str(count_error))
                    try:
                        cr.rollback()
                        cr.execute("SELECT COUNT(*) FROM vendor_bill_migration_line WHERE status = 'migrated'")
                        total_migrated = cr.fetchone()[0] if cr.rowcount > 0 else 0
                    except:
                        total_migrated = 0
                
                try:
                    total_errors = MigrationBill.search_count([
                        ('status', '=', 'error')
                    ])
                except Exception as count_error:
                    _logger.warning("Error counting error bills: %s", str(count_error))
                    try:
                        cr.rollback()
                        cr.execute("SELECT COUNT(*) FROM vendor_bill_migration_line WHERE status = 'error'")
                        total_errors = cr.fetchone()[0] if cr.rowcount > 0 else 0
                    except:
                        total_errors = 0
                
                import json
                status_data = {
                    'total_queued': total_queued,
                    'migrating_now': migrating_bill,
                    'migrating_bill_details': migrating_bill_details,
                    'total_migrated': total_migrated,
                    'total_errors': total_errors,
                }
                
                return request.make_response(
                    json.dumps(status_data, indent=2),
                    headers=[
                        ('Content-Type', 'application/json; charset=utf-8'),
                    ]
                )
            finally:
                cr.close()
            
        except Exception as e:
            _logger.error("Error in vendor bill migration status: %s", str(e), exc_info=True)
            import json
            return request.make_response(
                json.dumps({'error': str(e)}),
                headers=[
                    ('Content-Type', 'application/json; charset=utf-8'),
                ]
            )

    @http.route('/migration/process_one_system_type', type='http', auth='public', methods=['GET'], csrf=False)
    def process_one_system_type(self, **kwargs):
        """Process one system type from the queue synchronously"""
        try:
            db = kwargs.get('db')
            if not db:
                return request.make_response(
                    'ERROR: Database not specified. Use: /migration/process_one_system_type?db=your_database_name\n',
                    headers=[('Content-Type', 'text/plain; charset=utf-8')]
                )
            
            from odoo.api import Environment
            from odoo import sql_db
            try:
                db_conn = sql_db.db_connect(db)
                cr = db_conn.cursor()
            except Exception as reg_error:
                return request.make_response(
                    f'ERROR: Database "{db}" not found: {str(reg_error)}\n',
                    headers=[('Content-Type', 'text/plain; charset=utf-8')]
                )
            
            try:
                env = Environment(cr, 1, {})
                MigrationSystemType = env['amc.system.type.migration.line']
                
                # Find queued migration
                system_type_to_process = MigrationSystemType.search([
                    ('status', '=', 'queued')
                ], limit=1, order='id asc')
                
                if not system_type_to_process:
                    return request.make_response(
                        'No system types to migrate\nMigrating Now: None\n',
                        headers=[('Content-Type', 'text/plain; charset=utf-8')]
                    )
                
                system_type_name = system_type_to_process.uploaded_system_type_name
                _logger.info("🔄 Starting migration for system type %s", system_type_name)
                
                # Set status to migrating first
                system_type_to_process.write({
                    'status': 'migrating',
                    'status_message': 'Starting migration...',
                })
                cr.commit()
                
                try:
                    # Set status back to pending_migration (action_migrate requires it)
                    system_type_to_process.write({
                        'status': 'pending_migration',
                    })
                    cr.commit()
                    
                    # Call action_migrate
                    system_type_to_process.action_migrate()
                    cr.commit()
                    _logger.info("✅ Successfully migrated system type %s", system_type_name)
                    return request.make_response(
                        f'Migrating Now: {system_type_name} - DONE\n',
                        headers=[('Content-Type', 'text/plain; charset=utf-8')]
                    )
                except Exception as e:
                    error_msg = str(e)
                    _logger.error("❌ Error migrating system type %s: %s", system_type_name, error_msg)
                    _log_failed_system_type_migration(system_type_name, error_msg)
                    system_type_to_process.write({
                        'status': 'error',
                        'status_message': f'Migration failed: {error_msg[:200]}',
                        'error_message': error_msg[:500],
                    })
                    cr.commit()
                    return request.make_response(
                        f'Migrating Now: {system_type_name} - ERROR\n',
                        headers=[('Content-Type', 'text/plain; charset=utf-8')]
                    )
            finally:
                cr.close()
        except Exception as e:
            _logger.error("Error in process_one_system_type: %s", str(e), exc_info=True)
            return request.make_response(
                f'ERROR: {str(e)}\n',
                headers=[('Content-Type', 'text/plain; charset=utf-8')]
            )

    @http.route('/migration/status_system_type', type='http', auth='public', methods=['GET'], csrf=False)
    def get_system_type_status(self, **kwargs):
        """Get system type migration status"""
        try:
            db = kwargs.get('db')
            if not db:
                import json
                return request.make_response(
                    json.dumps({'error': 'Database not specified. Use: /migration/status_system_type?db=your_database_name'}),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            
            from odoo.api import Environment
            from odoo import sql_db
            try:
                db_conn = sql_db.db_connect(db)
                cr = db_conn.cursor()
            except Exception as reg_error:
                import json
                return request.make_response(
                    json.dumps({'error': f'Database "{db}" not found: {str(reg_error)}'}),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            
            try:
                env = Environment(cr, 1, {})
                MigrationSystemType = env['amc.system.type.migration.line']
                
                total_queued = MigrationSystemType.search_count([('status', '=', 'queued')])
                total_migrated = MigrationSystemType.search_count([('status', '=', 'migrated')])
                total_errors = MigrationSystemType.search_count([('status', '=', 'error')])
                
                currently_migrating = MigrationSystemType.search([
                    ('status', '=', 'migrating')
                ], limit=1, order='write_date desc')
                
                migrating_now = currently_migrating.uploaded_system_type_name if currently_migrating else 'None'
                
                status_data = {
                    'total_queued': total_queued,
                    'total_migrated': total_migrated,
                    'total_errors': total_errors,
                    'migrating_now': migrating_now,
                }
                
                import json
                return request.make_response(
                    json.dumps(status_data, indent=2),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            finally:
                cr.close()
        except Exception as e:
            _logger.error("Error in system type migration status: %s", str(e), exc_info=True)
            import json
            return request.make_response(
                json.dumps({'error': str(e)}),
                headers=[('Content-Type', 'application/json; charset=utf-8')]
            )

    @http.route('/migration/process_one_project', type='http', auth='public', methods=['GET'], csrf=False)
    def process_one_project(self, **kwargs):
        """Process one project from the queue synchronously"""
        try:
            db = kwargs.get('db')
            if not db:
                return request.make_response(
                    'ERROR: Database not specified. Use: /migration/process_one_project?db=your_database_name\n',
                    headers=[('Content-Type', 'text/plain; charset=utf-8')]
                )
            
            from odoo.api import Environment
            from odoo import sql_db
            try:
                db_conn = sql_db.db_connect(db)
                cr = db_conn.cursor()
            except Exception as reg_error:
                return request.make_response(
                    f'ERROR: Database "{db}" not found: {str(reg_error)}\n',
                    headers=[('Content-Type', 'text/plain; charset=utf-8')]
                )
            
            try:
                env = Environment(cr, 1, {})
                MigrationProject = env['project.migration.line']
                
                # Find queued migration
                project_to_process = MigrationProject.search([
                    ('status', '=', 'queued')
                ], limit=1, order='id asc')
                
                if not project_to_process:
                    return request.make_response(
                        'No projects to migrate\nMigrating Now: None\n',
                        headers=[('Content-Type', 'text/plain; charset=utf-8')]
                    )
                
                project_code = project_to_process.project_code
                _logger.info("🔄 Starting migration for project %s", project_code)
                
                # Set status to migrating first
                project_to_process.write({
                    'status': 'migrating',
                    'status_message': 'Starting migration...',
                })
                cr.commit()
                
                try:
                    # Call action_migrate
                    project_to_process.action_migrate()
                    cr.commit()
                    _logger.info("✅ Successfully migrated project %s", project_code)
                    return request.make_response(
                        f'Migrating Now: {project_code} - DONE\n',
                        headers=[('Content-Type', 'text/plain; charset=utf-8')]
                    )
                except Exception as e:
                    error_msg = str(e)
                    _logger.error("❌ Error migrating project %s: %s", project_code, error_msg)
                    _log_failed_project_migration(project_code, error_msg)
                    project_to_process.write({
                        'status': 'error',
                        'status_message': f'Migration failed: {error_msg[:200]}',
                        'error_message': error_msg[:500],
                    })
                    cr.commit()
                    return request.make_response(
                        f'Migrating Now: {project_code} - ERROR\n',
                        headers=[('Content-Type', 'text/plain; charset=utf-8')]
                    )
            finally:
                cr.close()
        except Exception as e:
            _logger.error("Error in process_one_project: %s", str(e), exc_info=True)
            return request.make_response(
                f'ERROR: {str(e)}\n',
                headers=[('Content-Type', 'text/plain; charset=utf-8')]
            )

    @http.route('/migration/status_project', type='http', auth='public', methods=['GET'], csrf=False)
    def get_project_status(self, **kwargs):
        """Get project migration status"""
        try:
            db = kwargs.get('db')
            if not db:
                import json
                return request.make_response(
                    json.dumps({'error': 'Database not specified. Use: /migration/status_project?db=your_database_name'}),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            
            from odoo.api import Environment
            from odoo import sql_db
            try:
                db_conn = sql_db.db_connect(db)
                cr = db_conn.cursor()
            except Exception as reg_error:
                import json
                return request.make_response(
                    json.dumps({'error': f'Database "{db}" not found: {str(reg_error)}'}),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            
            try:
                env = Environment(cr, 1, {})
                MigrationProject = env['project.migration.line']
                
                total_queued = MigrationProject.search_count([('status', '=', 'queued')])
                total_migrated = MigrationProject.search_count([('status', '=', 'migrated')])
                total_errors = MigrationProject.search_count([('status', '=', 'error')])
                
                currently_migrating = MigrationProject.search([
                    ('status', '=', 'migrating')
                ], limit=1, order='write_date desc')
                
                migrating_now = currently_migrating.project_code if currently_migrating else 'None'
                
                status_data = {
                    'total_queued': total_queued,
                    'total_migrated': total_migrated,
                    'total_errors': total_errors,
                    'migrating_now': migrating_now,
                }
                
                import json
                return request.make_response(
                    json.dumps(status_data, indent=2),
                    headers=[('Content-Type', 'application/json; charset=utf-8')]
                )
            finally:
                cr.close()
        except Exception as e:
            _logger.error("Error in project migration status: %s", str(e), exc_info=True)
            import json
            return request.make_response(
                json.dumps({'error': str(e)}),
                headers=[('Content-Type', 'application/json; charset=utf-8')]
            )


def _log_failed_project_migration(project_code, error_detail):
    """Log failed project migration to a file for later processing"""
    try:
        # Get log directory (use module directory/logs)
        module_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        log_dir = os.path.join(module_dir, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'failed_project_migrations.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {project_code} | {error_detail[:200]}\n")
        
        _logger.info("Failed project migration logged to: %s", log_file)
    except Exception as e:
        _logger.warning("Could not write to failed project migrations log: %s", str(e))


def _log_failed_rfq_migration(rfq_number, error_detail):
    """Log failed RFQ migration to a file for later processing"""
    try:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'failed_rfq_migrations.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {rfq_number} | {error_detail[:200]}\n")
        
        _logger.info("Failed RFQ migration logged to: %s", log_file)
    except Exception as e:
        _logger.warning("Could not write to failed RFQ migrations log: %s", str(e))


def _log_failed_estimation_migration(estimation_number, error_detail):
    """Log failed estimation migration to a file for later processing"""
    try:
        # Get log directory (use module directory/logs)
        module_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        log_dir = os.path.join(module_dir, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'failed_estimation_migrations.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {estimation_number} | {error_detail[:200]}\n")
        
        _logger.info("Failed estimation migration logged to: %s", log_file)
    except Exception as e:
        _logger.warning("Could not write to failed estimation migrations log: %s", str(e))


def _log_failed_invoice_migration(invoice_number, error_detail):
    """Log failed customer invoice migration to a file for later processing"""
    try:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'failed_invoice_migrations.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {invoice_number} | {error_detail[:200]}\n")
        
        _logger.info("Failed invoice migration logged to: %s", log_file)
    except Exception as e:
        _logger.warning("Could not write to failed invoice migrations log: %s", str(e))


def _log_failed_vendor_bill_migration(bill_number, error_detail):
    """Log failed vendor bill migration to a file for later processing"""
    try:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'failed_vendor_bill_migrations.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {bill_number} | {error_detail[:200]}\n")
        
        _logger.info("Failed vendor bill migration logged to: %s", log_file)
    except Exception as e:
        _logger.warning("Could not write to failed vendor bill migrations log: %s", str(e))

