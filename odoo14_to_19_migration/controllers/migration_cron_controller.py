# -*- coding: utf-8 -*-

import logging
import os
from datetime import datetime
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


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
