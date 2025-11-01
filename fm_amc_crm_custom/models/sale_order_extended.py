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
        """Update is_estimation_order, copy fields and lines from estimation when linked"""
        if self.estimation_id:
            self.is_estimation_order = True
            if not self.estimated_hours:
                self.estimated_hours = self.estimation_id.estimated_hours
            # Automatically load lines when estimation is selected
            if self.estimation_id.line_ids:
                self.with_context(from_onchange=True).action_load_estimation_lines()
    
    def action_load_estimation_lines(self):
        """Action to copy all estimation lines to quotation - can be called from button or onchange"""
        if not self.estimation_id:
            return {'warning': {'title': 'Warning', 'message': 'Please select an estimation first.'}}
        
        # Get all estimation lines (includes project, consumable, and expense)
        estimation_lines = self.estimation_id.line_ids
        
        if not estimation_lines:
            return {'warning': {'title': 'Warning', 'message': f'Estimation {self.estimation_id.name} has no lines to copy.'}}
        
        _logger.info(f"Copying {len(estimation_lines)} lines from estimation {self.estimation_id.name}")
        
        # Clear existing order lines first
        self.order_line = [(5, 0, 0)]
        
        # Copy all estimation lines to order lines
        order_lines = []
        for est_line in estimation_lines:
            # Prepare line values - match the format used in action_create_quotation
            line_vals = {
                'product_id': est_line.product_id.id if est_line.product_id else False,
                'name': est_line.name or '',
                'product_uom_qty': est_line.product_uom_qty or 1.0,
                'price_unit': est_line.price_unit or 0.0,
            }
            
            # Set UoM - use estimation UoM or product default UoM
            # In sale.order.line, the field is product_uom_id, not product_uom
            if est_line.product_uom:
                line_vals['product_uom_id'] = est_line.product_uom.id
            elif est_line.product_id and est_line.product_id.uom_id:
                line_vals['product_uom_id'] = est_line.product_id.uom_id.id
            
            # Add taxes if available
            # In sale.order.line, taxes field might need to be set via write or may not be available in create
            # Let's set it after creation or skip for now and let product onchange set it
            # Note: taxes are typically set via product_id onchange in sale.order.line
            
            order_lines.append((0, 0, line_vals))
            _logger.info(f"Added line: {line_vals.get('name', 'N/A')} - Fields: {list(line_vals.keys())}")
            # Debug: Check for any incorrect field names
            if 'product_uom' in line_vals:
                _logger.error(f"ERROR: Found 'product_uom' in line_vals! This should be 'product_uom_id'")
        
        # Set all order lines at once using One2many command format
        if order_lines:
            self.order_line = order_lines
            _logger.info(f"Successfully set {len(order_lines)} order lines")
            
            # Set taxes after lines are created
            # Note: In Odoo, tax_id is the correct field, but we need to set it after creation
            estimation_lines_list = list(estimation_lines)
            for i, sol in enumerate(self.order_line):
                if i < len(estimation_lines_list):
                    est_line = estimation_lines_list[i]
                    if est_line.tax_id:
                        sol.write({'tax_id': [(6, 0, est_line.tax_id.ids)]})
            # Only return notification if called from button (not onchange)
            if hasattr(self, '_context') and not self.env.context.get('from_onchange'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success',
                        'message': f'{len(order_lines)} lines copied from estimation.',
                        'type': 'success',
                        'sticky': False,
                    }
                }
        
        return False

    @api.depends('estimation_id')
    def _compute_estimated_value(self):
        """Compute estimated value from estimation"""
        for order in self:
            if order.estimation_id:
                order.estimated_value = order.estimation_id.amount_untaxed
                _logger.info(f"Estimated value computed: {order.estimated_value} for estimation {order.estimation_id.name}")
            else:
                order.estimated_value = 0.0

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

