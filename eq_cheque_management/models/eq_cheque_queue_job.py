# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class EqChequeIncomingQueueJob(models.Model):
    """Queue Job methods for incoming cheques"""
    _name = 'eq.cheque.incoming'
    _inherit = 'eq.cheque.incoming'

    def enqueue_pdc_deposit_jobs(self):
        """Enqueue deposit jobs for PDC cheques that are due"""
        today = date.today()
        
        # Find cheques that need to be deposited
        cheques = self.search([
            ('state', '=', 'registered'),
            ('cheque_type', '=', 'pdc'),
            ('cheque_date', '<=', today),
        ])
        
        _logger.info('Found %s PDC incoming cheques to auto-deposit', len(cheques))
        
        for cheque in cheques:
            try:
                # Enqueue deposit job
                cheque.with_delay()._auto_deposit_pdc()
            except Exception as e:
                _logger.error('Error enqueueing deposit job for cheque %s: %s', cheque.name, str(e))
        
        return len(cheques)

    def _auto_deposit_pdc(self):
        """Auto-deposit PDC cheque (queue job method)"""
        self.ensure_one()
        
        if self.state != 'registered':
            _logger.warning('Cheque %s is not in registered state, skipping auto-deposit', self.name)
            return False
        
        if self.cheque_type != 'pdc':
            _logger.warning('Cheque %s is not a PDC, skipping auto-deposit', self.name)
            return False
        
        try:
            self.action_deposit()
            _logger.info('Auto-deposited incoming PDC cheque %s', self.name)
            return True
        except Exception as e:
            _logger.error('Error auto-depositing cheque %s: %s', self.name, str(e))
            raise


class EqChequeOutgoingQueueJob(models.Model):
    """Queue Job methods for outgoing cheques"""
    _name = 'eq.cheque.outgoing'
    _inherit = 'eq.cheque.outgoing'

    def enqueue_pdc_deposit_jobs(self):
        """Enqueue deposit jobs for PDC cheques that are due"""
        today = date.today()
        
        # Find cheques that need to be deposited
        cheques = self.search([
            ('state', '=', 'registered'),
            ('cheque_type', '=', 'pdc'),
            ('cheque_date', '<=', today),
        ])
        
        _logger.info('Found %s PDC outgoing cheques to auto-deposit', len(cheques))
        
        for cheque in cheques:
            try:
                # Enqueue deposit job
                cheque.with_delay()._auto_deposit_pdc()
            except Exception as e:
                _logger.error('Error enqueueing deposit job for cheque %s: %s', cheque.name, str(e))
        
        return len(cheques)

    def _auto_deposit_pdc(self):
        """Auto-deposit PDC cheque (queue job method)"""
        self.ensure_one()
        
        if self.state != 'registered':
            _logger.warning('Cheque %s is not in registered state, skipping auto-deposit', self.name)
            return False
        
        if self.cheque_type != 'pdc':
            _logger.warning('Cheque %s is not a PDC, skipping auto-deposit', self.name)
            return False
        
        try:
            self.action_deposit()
            _logger.info('Auto-deposited outgoing PDC cheque %s', self.name)
            return True
        except Exception as e:
            _logger.error('Error auto-depositing cheque %s: %s', self.name, str(e))
            raise


class EqChequeCronJob(models.Model):
    """Cron job model for auto-depositing PDC cheques"""
    _name = 'eq.cheque.cron'
    _description = 'Cheque Cron Job Model'

    def enqueue_pdc_deposit_jobs(self):
        """Enqueue deposit jobs for both incoming and outgoing PDC cheques"""
        incoming_count = self.env['eq.cheque.incoming'].enqueue_pdc_deposit_jobs()
        outgoing_count = self.env['eq.cheque.outgoing'].enqueue_pdc_deposit_jobs()
        
        _logger.info('Enqueued %s incoming and %s outgoing PDC deposit jobs', incoming_count, outgoing_count)
        return True

