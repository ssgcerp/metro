# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Estimation fields
    estimation_id = fields.Many2one('fm.amc.estimation', string='Estimation', tracking=True,
                                    help='Linked estimation for this quotation')
    estimated_value = fields.Monetary(string='Estimated', compute='_compute_estimated_value',
                                      store=False, currency_field='currency_id',
                                      help='Total estimated value from the linked estimation (untaxed)')
    is_estimation_order = fields.Boolean(string='Estimation', default=False, readonly=False,
                                        help='Check this if this quotation is linked to an estimation')
    
    # Additional Quotation Fields
    attention_id = fields.Many2one('res.partner', string='Attention',
                                   domain="[('parent_id', '=', partner_id), ('is_company', '=', False)]",
                                   help='Attention/Contact person')
    client_id = fields.Many2one('res.partner', string='Client',
                               help='Client for this quotation')
    consultants_ids = fields.Many2many('res.partner', 'sale_order_consultants_rel',
                                      'order_id', 'partner_id', string='Consultants',
                                      help='Consultants involved in this quotation')
    is_project_order = fields.Boolean(string='Project Order', default=False,
                                      help='Is this a project order?')
    estimated_hours = fields.Float(string='Estimated Hours', default=0.0,
                                   help='Estimated hours for this quotation')
    direct_order = fields.Boolean(string='Direct Order', default=False,
                                 help='Is this a direct order?')
    revised_quotation = fields.Boolean(string='Revised Quotation', default=False,
                                      help='Is this a revised quotation?')
    lumpsum = fields.Boolean(string='Lumpsum', default=False,
                            help='Is this a lumpsum quotation?')
    with_brand = fields.Boolean(string='Brand', default=False,
                               help='Include brand in quotation?')
    with_stamp = fields.Boolean(string='With Stamp', default=False,
                               help='Include stamp in quotation?')
    with_unit_price = fields.Boolean(string='With Unit Price', default=False,
                                    help='Show unit price in quotation?')
    with_uom = fields.Boolean(string='With UoM', default=False,
                              help='Show unit of measure in quotation?')
    validity_date = fields.Date(string='Expiration Date', 
                               help='Date until which this quotation is valid')

    # Workflow tracking fields
    printed_without_approval = fields.Boolean(string='Printed Without Approval', default=False,
                                             help='Whether quotation was printed before approval')

    # Quotation stage (replacing state field for custom workflow)
    quotation_stage_id = fields.Many2one('sale.quotation.stage', string='Quotation Stage', 
                                        tracking=True, copy=False,
                                        default=lambda self: self._get_default_quotation_stage(),
                                        help='Current stage in the quotation workflow')

    # Stage flags for button visibility
    is_draft_stage = fields.Boolean(string='Is Draft Stage', compute='_compute_stage_flags', store=False)
    is_pending_approval_stage = fields.Boolean(string='Is Pending Approval Stage', compute='_compute_stage_flags', store=False)
    is_quotation_stage = fields.Boolean(string='Is Quotation Stage', compute='_compute_stage_flags', store=False)
    is_quotation_sent_stage = fields.Boolean(string='Is Quotation Sent Stage', compute='_compute_stage_flags', store=False)
    is_sales_order_stage = fields.Boolean(string='Is Sales Order Stage', compute='_compute_stage_flags', store=False)
    is_locked = fields.Boolean(string='Is Locked', compute='_compute_stage_flags', store=False)

    @api.model
    def _get_default_quotation_stage(self):
        """Get default quotation stage"""
        try:
            stage = self.env['sale.quotation.stage'].search([('is_draft_stage', '=', True)], limit=1)
            return stage.id if stage else False
        except Exception:
            return False

    @api.depends('quotation_stage_id', 'estimation_id')
    def _compute_stage_flags(self):
        """Compute stage flags for button visibility"""
        for order in self:
            stage = order.quotation_stage_id
            order.is_draft_stage = stage.code == 'draft' if stage else False
            order.is_pending_approval_stage = stage.code == 'pending_approval' if stage else False
            order.is_quotation_stage = stage.code == 'quotation' if stage else False
            order.is_quotation_sent_stage = stage.code == 'quotation_sent' if stage else False
            order.is_sales_order_stage = stage.code == 'sales_order' if stage else False
            order.is_locked = stage.is_locked_stage if stage else False

    @api.onchange('is_estimation_order')
    def _onchange_is_estimation_order(self):
        """Clear estimation_id when is_estimation_order is unchecked"""
        if not self.is_estimation_order:
            self.estimation_id = False
            self.estimated_hours = 0.0

    @api.onchange('estimation_id')
    def _onchange_estimation_id(self):
        """Update is_estimation_order and copy fields from estimation when linked"""
        if self.estimation_id:
            self.is_estimation_order = True
            if not self.estimated_hours:
                self.estimated_hours = self.estimation_id.estimated_hours

    @api.depends('estimation_id')
    def _compute_estimated_value(self):
        """Compute estimated value from estimation"""
        for order in self:
            if order.estimation_id:
                order.estimated_value = order.estimation_id.amount_untaxed
                _logger.info(f"Estimated value computed: {order.estimated_value} for estimation {order.estimation_id.name}")
            else:
                order.estimated_value = 0.0
    
    @api.onchange('estimation_id')
    def _onchange_estimation_id(self):
        """Copy fields from estimation when linked"""
        if self.estimation_id:
            if not self.estimated_hours:
                self.estimated_hours = self.estimation_id.estimated_hours

    def action_send_for_approval(self):
        """Move quotation to Pending Approval stage"""
        pending_stage = self.env['sale.quotation.stage'].search([('code', '=', 'pending_approval')], limit=1)
        if not pending_stage:
            raise ValidationError("Pending Approval stage not found. Please check stage configuration.")
        self.write({'quotation_stage_id': pending_stage.id})
        return True

    def action_approve(self):
        """Move quotation to Quotation stage"""
        quotation_stage = self.env['sale.quotation.stage'].search([('code', '=', 'quotation')], limit=1)
        if not quotation_stage:
            raise ValidationError("Quotation stage not found. Please check stage configuration.")
        self.write({'quotation_stage_id': quotation_stage.id})
        return True

    def action_reject(self):
        """Move quotation back to Draft stage"""
        draft_stage = self.env['sale.quotation.stage'].search([('code', '=', 'draft')], limit=1)
        if not draft_stage:
            raise ValidationError("Draft stage not found. Please check stage configuration.")
        self.write({'quotation_stage_id': draft_stage.id})
        return True

    def action_mark_quotation_sent(self):
        """Move quotation to Quotation Sent stage"""
        sent_stage = self.env['sale.quotation.stage'].search([('code', '=', 'quotation_sent')], limit=1)
        if not sent_stage:
            raise ValidationError("Quotation Sent stage not found. Please check stage configuration.")
        self.write({'quotation_stage_id': sent_stage.id})
        return True

    def action_cancel_quotation(self):
        """Cancel the quotation"""
        cancelled_stage = self.env['sale.quotation.stage'].search([('code', '=', 'cancelled')], limit=1)
        if not cancelled_stage:
            raise ValidationError("Cancelled stage not found. Please check stage configuration.")
        self.write({'quotation_stage_id': cancelled_stage.id})
        return True

    def action_reset_to_draft(self):
        """Reset quotation to draft"""
        draft_stage = self.env['sale.quotation.stage'].search([('code', '=', 'draft')], limit=1)
        if not draft_stage:
            raise ValidationError("Draft stage not found. Please check stage configuration.")
        self.write({'quotation_stage_id': draft_stage.id})
        return True

    def action_mark_printed(self):
        """Mark quotation as printed"""
        if self.quotation_stage_id.code == 'pending_approval':
            self.printed_without_approval = True
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

