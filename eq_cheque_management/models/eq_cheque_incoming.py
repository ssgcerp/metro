# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class EqChequeIncoming(models.Model):
    _name = 'eq.cheque.incoming'
    _description = 'Incoming Cheque'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'cheque_date desc, id desc'
    _check_company_auto = True

    # Basic Fields
    name = fields.Char(
        string='Cheque Number',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        help='Unique sequence number for incoming cheque (IN/YYYY/0001)',
    )
    cheque_number = fields.Char(
        string='Cheque Number',
        required=True,
        tracking=True,
        help='Physical cheque number from the cheque',
    )
    cheque_type = fields.Selection([
        ('cdc', 'CDC - Current Date Cheque'),
        ('pdc', 'PDC - Post Dated Cheque'),
    ], string='Cheque Type', required=True, default='cdc', tracking=True)
    
    # Partner & Company
    partner_id = fields.Many2one(
        'res.partner',
        string='Payee',
        required=True,
        tracking=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
    )
    
    # Dates
    cheque_date = fields.Date(
        string='Cheque Date',
        required=True,
        tracking=True,
        help='Date written on the cheque',
    )
    cheque_receive_date = fields.Date(
        string='Cheque Received Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
        help='Date when cheque was received',
    )
    
    # Financial Fields
    amount = fields.Monetary(
        string='Amount',
        required=True,
        tracking=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    
    # Journal & Accounts
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        domain="[('type', '=', 'bank')]",
        tracking=True,
        check_company=True,
    )
    debit_account_id = fields.Many2one(
        'account.account',
        string='Debit Account',
        required=True,
        tracking=True,
        check_company=True,
        help='Account to debit when cheque is registered (typically Bank account)',
    )
    
    # Contract Integration
    contract_id = fields.Many2one(
        'amc.contract',
        string='AMC / Contract',
        tracking=True,
        help='Link this cheque to an AMC or Service Contract',
    )
    
    # State & Workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('registered', 'Registered'),
        ('deposited', 'Deposited'),
        ('done', 'Done'),
        ('bounced', 'Bounced'),
        ('returned', 'Returned'),
        ('cancel', 'Cancelled'),
    ], string='State', default='draft', required=True, tracking=True, copy=False)
    
    # Accounting
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True,
        copy=False,
        check_company=True,
        help='Journal entry created for this cheque',
    )
    move_line_ids = fields.One2many(
        'account.move.line',
        'move_id',
        related='move_id.line_ids',
        string='Journal Items',
        readonly=True,
    )
    move_line_count = fields.Integer(
        string='Journal Items Count',
        compute='_compute_move_line_count',
        store=False,
    )
    
    # Computed Fields
    is_registered = fields.Boolean(compute='_compute_state_booleans', store=True)
    is_deposited = fields.Boolean(compute='_compute_state_booleans', store=True)
    is_done = fields.Boolean(compute='_compute_state_booleans', store=True)
    is_bounced = fields.Boolean(compute='_compute_state_booleans', store=True)
    is_returned = fields.Boolean(compute='_compute_state_booleans', store=True)
    is_cancelled = fields.Boolean(compute='_compute_state_booleans', store=True)
    
    # Description
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('cheque_number_uniq', 'UNIQUE(cheque_number, company_id)',
         'Cheque number must be unique per company!'),
    ]

    @api.depends('move_id', 'move_id.line_ids')
    def _compute_move_line_count(self):
        """Compute count of journal items"""
        for record in self:
            record.move_line_count = len(record.move_line_ids) if record.move_line_ids else 0

    @api.depends('state')
    def _compute_state_booleans(self):
        """Compute boolean fields for state checking"""
        for record in self:
            record.is_registered = record.state == 'registered'
            record.is_deposited = record.state == 'deposited'
            record.is_done = record.state == 'done'
            record.is_bounced = record.state == 'bounced'
            record.is_returned = record.state == 'returned'
            record.is_cancelled = record.state == 'cancel'


    @api.model_create_multi
    def create(self, vals_list):
        """Generate sequence number on create"""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                config = self._get_cheque_config(vals.get('company_id', self.env.company.id))
                if config and config.incoming_sequence_id:
                    vals['name'] = config.incoming_sequence_id.next_by_id()
                else:
                    # Fallback sequence
                    vals['name'] = self.env['ir.sequence'].next_by_code('eq.cheque.incoming') or _('New')
        return super().create(vals_list)

    def _get_cheque_config(self, company_id=None):
        """Get cheque configuration for company, create if not exists"""
        company = self.env['res.company'].browse(company_id) if company_id else self.env.company
        config = self.env['eq.cheque.config'].search([('company_id', '=', company.id)], limit=1)
        
        # Create configuration if it doesn't exist
        if not config:
            # Get default sequences
            incoming_sequence = self.env['ir.sequence'].search([
                ('code', '=', 'eq.cheque.incoming')
            ], limit=1)
            
            outgoing_sequence = self.env['ir.sequence'].search([
                ('code', '=', 'eq.cheque.outgoing')
            ], limit=1)
            
            config = self.env['eq.cheque.config'].create({
                'company_id': company.id,
                'incoming_sequence_id': incoming_sequence.id if incoming_sequence else False,
                'outgoing_sequence_id': outgoing_sequence.id if outgoing_sequence else False,
            })
        
        return config

    @api.constrains('cheque_number', 'company_id')
    def _check_cheque_number_unique(self):
        """Ensure cheque number is unique per company"""
        for record in self:
            if self.search_count([
                ('cheque_number', '=', record.cheque_number),
                ('company_id', '=', record.company_id.id),
                ('id', '!=', record.id),
            ]) > 0:
                raise ValidationError('Cheque number %s already exists for company %s!' % (
                    record.cheque_number, record.company_id.name))

    @api.constrains('amount')
    def _check_amount(self):
        """Ensure amount is positive"""
        for record in self:
            if record.amount <= 0:
                raise ValidationError('Cheque amount must be greater than zero!')

    @api.constrains('journal_id')
    def _check_journal_type(self):
        """Ensure journal is a bank journal"""
        for record in self:
            if record.journal_id and record.journal_id.type != 'bank':
                raise ValidationError('Journal must be a Bank journal!')

    def action_register(self):
        """Register cheque - create journal entry"""
        for record in self:
            if record.state != 'draft':
                raise UserError('Only draft cheques can be registered!')
            
            config = record._get_cheque_config()
            if not config:
                raise UserError('Cheque configuration not found for company %s!' % record.company_id.name)
            
            # Create journal entry
            move = record._create_register_move(config)
            move.action_post()
            record.write({
                'state': 'registered',
                'move_id': move.id,
            })
            
            _logger.info('Incoming cheque %s registered with move %s', record.name, move.name)
        return True

    def _create_register_move(self, config):
        """Create journal entry for registered incoming cheque"""
        self.ensure_one()
        
        # Get partner receivable account
        partner_account = self.partner_id.property_account_receivable_id
        if not partner_account:
            raise UserError('Partner %s does not have a receivable account configured!' % self.partner_id.name)
        
        # For PDC: Use PDC Receivable account
        # For CDC: Use debit account (bank) directly or clearing account
        if self.cheque_type == 'pdc':
            debit_account = config.pdc_receivable_account_id
            if not debit_account:
                raise UserError('PDC Receivable Account not configured!')
        else:
            # CDC: Can use clearing account or direct bank account
            debit_account = config.pdc_clearing_account_id or self.debit_account_id
            if not debit_account:
                raise UserError('PDC Clearing Account or Debit Account must be configured!')
        
        # Create move with lines in standard Odoo way
        move_vals = {
            'move_type': 'entry',
            'date': self.cheque_receive_date,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'ref': '%s - %s' % (self.name, self.cheque_number),
            'line_ids': [
                (0, 0, {
                    'account_id': debit_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': self.amount,
                    'credit': 0.0,
                    'name': '%s - %s' % (self.name, 'Registered'),
                }),
                (0, 0, {
                    'account_id': partner_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': 0.0,
                    'credit': self.amount,
                    'name': '%s - %s' % (self.name, 'Registered'),
                }),
            ],
        }
        return self.env['account.move'].with_company(self.company_id).create(move_vals)

    def action_deposit(self):
        """Deposit cheque - move from PDC/Clearing to Bank"""
        for record in self:
            if record.state != 'registered':
                raise UserError('Only registered cheques can be deposited!')
            
            if not record.move_id:
                raise UserError('Journal entry not found for this cheque!')
            
            config = record._get_cheque_config()
            if not config:
                raise UserError('Cheque configuration not found!')
            
            # Create deposit move
            move = record._create_deposit_move(config)
            record.write({'state': 'deposited'})
            move.action_post()
            
            _logger.info('Incoming cheque %s deposited with move %s', record.name, move.name)
        return True

    def _create_deposit_move(self, config):
        """Create journal entry for deposited cheque"""
        self.ensure_one()
        
        # Get source account (PDC Receivable or Clearing)
        if self.cheque_type == 'pdc':
            source_account = config.pdc_receivable_account_id
        else:
            source_account = config.pdc_clearing_account_id or self.debit_account_id
        
        if not source_account:
            raise UserError('Source account not configured!')
        
        # Create move: Bank (DR) <- PDC/Clearing (CR)
        move = self.env['account.move'].with_company(self.company_id).create({
            'move_type': 'entry',
            'date': fields.Date.today(),
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'ref': '%s - %s - Deposited' % (self.name, self.cheque_number),
        })
        # Add lines
        self.env['account.move.line'].create([
            {
                'move_id': move.id,
                'account_id': self.debit_account_id.id,
                'partner_id': self.partner_id.id,
                'debit': self.amount,
                'credit': 0.0,
                'name': '%s - %s - Deposited' % (self.name, self.cheque_number),
            },
            {
                'move_id': move.id,
                'account_id': source_account.id,
                'partner_id': self.partner_id.id,
                'debit': 0.0,
                'credit': self.amount,
                'name': '%s - %s - Deposited' % (self.name, self.cheque_number),
            },
        ])
        return move

    def action_done(self):
        """Mark cheque as done (cleared)"""
        for record in self:
            if record.state not in ('registered', 'deposited'):
                raise UserError('Only registered or deposited cheques can be marked as done!')
            
            record.write({'state': 'done'})
            _logger.info('Incoming cheque %s marked as done', record.name)
        return True

    def action_bounce(self):
        """Bounce cheque - reverse accounting entry"""
        for record in self:
            if record.state != 'registered':
                raise UserError('Only registered cheques can be bounced!')
            
            if not record.move_id:
                raise UserError('Journal entry not found!')
            
            config = record._get_cheque_config()
            if not config:
                raise UserError('Cheque configuration not found!')
            
            # Reverse the register move by creating a reversal entry
            try:
                reversal_move = record.move_id._reverse_moves(
                    default_values_list=[{'ref': '%s - %s - Bounced' % (record.name, record.cheque_number)}]
                )
                reversal_move.action_post()
            except AttributeError:
                # Fallback: Use reversal wizard if _reverse_moves doesn't exist
                reversal_wizard = self.env['account.move.reversal'].with_context(
                    active_model='account.move',
                    active_ids=record.move_id.ids,
                ).create({
                    'ref': '%s - %s - Bounced' % (record.name, record.cheque_number),
                })
                reversal_move = reversal_wizard.reverse_moves()
                reversal_move.action_post()
            
            record.write({'state': 'bounced'})
            _logger.info('Incoming cheque %s bounced', record.name)
        return True

    def action_return(self):
        """Return cheque - cancel journal entry if allowed"""
        for record in self:
            if record.state != 'registered':
                raise UserError('Only registered cheques can be returned!')
            
            if not record.move_id:
                raise UserError('Journal entry not found!')
            
            config = record._get_cheque_config()
            if not config:
                raise UserError('Cheque configuration not found!')
            
            # Cancel or reverse move based on configuration
            if config.allow_cancel_journal_entries and record.move_id.state == 'posted':
                try:
                    record.move_id.button_draft()
                    record.move_id.button_cancel()
                except Exception as e:
                    _logger.error('Cannot cancel move %s: %s', record.move_id.name, str(e))
                    raise UserError('Cannot cancel journal entry: %s' % str(e))
            else:
                # Reverse the move by creating a reversal entry
                try:
                    reversal_move = record.move_id._reverse_moves(
                        default_values_list=[{'ref': '%s - %s - Returned' % (record.name, record.cheque_number)}]
                    )
                    reversal_move.action_post()
                except AttributeError:
                    # Fallback: Use reversal wizard if _reverse_moves doesn't exist
                    reversal_wizard = self.env['account.move.reversal'].with_context(
                        active_model='account.move',
                        active_ids=record.move_id.ids,
                    ).create({
                        'ref': '%s - %s - Returned' % (record.name, record.cheque_number),
                    })
                    reversal_move = reversal_wizard.reverse_moves()
                    reversal_move.action_post()
            
            record.write({'state': 'returned'})
            _logger.info('Incoming cheque %s returned', record.name)
        return True

    def action_cancel(self):
        """Cancel cheque"""
        for record in self:
            if record.state == 'done':
                raise UserError('Cannot cancel a cheque that is already done!')
            
            if record.move_id and record.move_id.state == 'posted':
                raise UserError('Cannot cancel cheque with posted journal entry!')
            
            record.write({'state': 'cancel'})
            _logger.info('Incoming cheque %s cancelled', record.name)
        return True

    def action_view_journal_items(self):
        """Open journal items"""
        self.ensure_one()
        action = {
            'name': 'Journal Items',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': [('move_id', '=', self.move_id.id)] if self.move_id else [('id', '=', False)],
        }
        return action

    def action_print_cheque(self):
        """Open cheque print wizard (for incoming cheques, typically not printed but available if needed)"""
        self.ensure_one()
        amount_words = self.currency_id.amount_to_text(self.amount) if self.currency_id and self.amount else ""
        return {
            'name': 'Print Cheque',
            'type': 'ir.actions.act_window',
            'res_model': 'cheque.print',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_pay_to': self.partner_id.name,
                'default_amount': self.amount,
                'default_currency_id': self.currency_id.id,
                'default_amt_2_words': amount_words,
                'default_cheque_date': self.cheque_date,
                'default_date_on_cheque': self.cheque_date,
                'default_customer_id': self.partner_id.id,
            }
        }

