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
    decline_reason = fields.Text(string='Decline Reason', 
                                help='Reason for declining the quotation')
    
    # Project field (for estimation integration)
    project_id = fields.Many2one('project.project', string='Project', tracking=True,
                                help='Related Project',
                                domain="[('partner_id', '=', partner_id)]")
    
    # Additional Details fields
    subject = fields.Char(string='Subject', help='Subject for the quotation')
    projectconfirm_move = fields.Char(string='Projectconfirm_move', help='Project confirmation move')
    work_location = fields.Char(string='Work Location', help='Location where work will be performed')
    description = fields.Text(string='Description', help='Description of the quotation')
    inclusion = fields.Text(string='Inclusion', help='Items included in the quotation')
    exclusion = fields.Text(string='Exclusion', help='Items excluded from the quotation')
    thanks_and_regards = fields.Text(string='Thanks and Regards', help='Closing message for the quotation')

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
    is_declined_stage = fields.Boolean(string='Is Declined Stage', compute='_compute_stage_flags', store=False)
    is_cancelled_stage = fields.Boolean(string='Is Cancelled Stage', compute='_compute_stage_flags', store=False)
    is_locked = fields.Boolean(string='Is Locked', compute='_compute_stage_flags', store=False)

    @api.model
    def _get_default_quotation_stage(self):
        """Get default quotation stage"""
        try:
            stage = self.env['sale.quotation.stage'].search([('is_draft_stage', '=', True)], limit=1)
            return stage.id if stage else False
        except Exception:
            return False

    @api.depends('quotation_stage_id')
    def _compute_stage_flags(self):
        """Compute stage flags for button visibility"""
        for order in self:
            stage = order.quotation_stage_id
            if stage:
                order.is_draft_stage = (stage.code == 'draft')
                order.is_pending_approval_stage = (stage.code == 'pending_approval')
                order.is_quotation_stage = (stage.code == 'quotation')
                order.is_quotation_sent_stage = (stage.code == 'quotation_sent')
                order.is_sales_order_stage = (stage.code == 'sales_order')
                order.is_declined_stage = (stage.code == 'declined')
                order.is_cancelled_stage = (stage.code == 'cancelled')
                order.is_locked = stage.is_locked_stage
            else:
                order.is_draft_stage = False
                order.is_pending_approval_stage = False
                order.is_quotation_stage = False
                order.is_quotation_sent_stage = False
                order.is_sales_order_stage = False
                order.is_declined_stage = False
                order.is_cancelled_stage = False
                order.is_locked = False

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
        estimation_lines_list = list(estimation_lines)
        
        for est_line in estimation_lines_list:
            # Prepare line values - match the format used in action_create_quotation
            # IMPORTANT: Set name AFTER product_id in the dict to ensure it overrides product defaults
            line_vals = {
                'product_id': est_line.product_id.id if est_line.product_id else False,
                'product_uom_qty': est_line.product_uom_qty or 1.0,
                'price_unit': est_line.price_unit or 0.0,
            }
            
            # Set UoM - use estimation UoM or product default UoM
            # In sale.order.line, the field is product_uom_id, not product_uom
            if est_line.product_uom:
                line_vals['product_uom_id'] = est_line.product_uom.id
            elif est_line.product_id and est_line.product_id.uom_id:
                line_vals['product_uom_id'] = est_line.product_id.uom_id.id
            
            # Set description/name - CRITICAL: This must be the exact description from estimation
            # The order in dict doesn't matter, but we set it explicitly to ensure it's copied
            if est_line.name:
                # Use the exact description from estimation, not product default
                line_vals['name'] = est_line.name.strip() if est_line.name else ''
            
            # Note: tax_id cannot be set in One2many command (0,0,vals) - must be set after creation
            
            order_lines.append((0, 0, line_vals))
            _logger.info(f"Added line: {est_line.name or 'N/A'} - Fields: {list(line_vals.keys())}")
            # Debug: Check for any incorrect field names
            if 'product_uom' in line_vals:
                _logger.error(f"ERROR: Found 'product_uom' in line_vals! This should be 'product_uom_id'")
        
        # Set all order lines at once using One2many command format
        if order_lines:
            self.order_line = order_lines
            _logger.info(f"Successfully set {len(order_lines)} order lines")
            
            # Force update descriptions after lines are created
            # This ensures description persists even if product_id_change tried to override it
            # We need to explicitly set the name field to override any product defaults
            estimation_lines_list_iter = iter(estimation_lines_list)
            for sol in self.order_line:
                est_line = next(estimation_lines_list_iter, None)
                if est_line and est_line.name:
                    # Set flag to preserve name and use context to prevent product_id_change override
                    sol._preserve_name_on_change = True
                    sol.with_context(from_estimation_load=True).name = est_line.name
                    _logger.info(f"Force set description for line: {est_line.name[:50] if est_line.name else 'N/A'}")
                    # Verify it was set correctly
                    if sol.name != est_line.name:
                        _logger.warning(f"Description mismatch! Expected: {est_line.name[:50]}, Got: {sol.name[:50] if sol.name else 'None'}")
            
            # Note: Taxes cannot be set in One2many commands or immediately after in onchange
            # They will be set from product defaults automatically when the form loads
            # If custom taxes from estimation are needed, user will need to set them manually
            # or we can add a button to sync taxes after record is saved
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
        """Move quotation to Pending Approval stage and generate quotation number
        
        Quotation number is generated here (not at creation) to ensure:
        - Quotations stay in draft without custom number until approved
        - Correct format is applied (standard or AMC based on estimation and AMC contract)
        - Works with or without estimation selected
        """
        # Generate quotation number when sending for approval
        # This ensures quotation number is only generated after approval request, not at creation
        
        config = self.env['sale.quotation.config'].get_config()
        
        # Check if quotation has estimation with AMC contract
        # AMC format should only be used if:
        # 1. Quotation has an estimation (estimation_id)
        # 2. AND that estimation has an AMC contract (amc_contract_id)
        use_amc_format = False
        if self.estimation_id and self.estimation_id.amc_contract_id:
            use_amc_format = True
        
        # Check if custom format is configured
        # Only attempt custom numbering if format_text (standard) or amc_quotation_format_text (AMC) is configured
        format_configured = False
        if use_amc_format:
            format_configured = bool(config.amc_quotation_format_text)
        else:
            format_configured = bool(config.format_text)
        
        # Only generate custom number if:
        # 1. Custom format is configured, AND
        # 2. Name is still default ("New" or empty), OR
        # 3. Name doesn't match the expected custom format
        needs_number = False
        if format_configured:
            if not self.name or self.name == 'New':
                needs_number = True
            else:
                # Check if it matches our custom format
                # Custom format should start with prefix or AMC prefix
                prefix = (config.prefix or '').upper()
                amc_prefix = (config.amc_prefix or '').upper()
                name_upper = (self.name or '').upper()
                
                # If it doesn't start with our prefix or AMC prefix, regenerate
                if prefix and not name_upper.startswith(prefix) and not name_upper.startswith(amc_prefix):
                    needs_number = True
        
        if needs_number and format_configured:
            # Get branch code from company if available
            branch_code = None
            if self.company_id and hasattr(self.company_id, 'branch_code') and self.company_id.branch_code:
                branch_code = self.company_id.branch_code
            elif self.company_id:
                # Try to get code from company name or use a default
                branch_code = getattr(self.company_id, 'abbreviation', None) or self.company_id.name[:3].upper() if self.company_id.name else None
            
            # Get year
            year = None
            if self.date_order:
                year = self.date_order.year
            else:
                year = fields.Date.today().year
            
            # Generate quotation number using configuration
            # This will return None if no format_text is configured
            quotation_number = config.generate_quotation_number(
                branch_code=branch_code,
                year=year,
                use_amc_format=use_amc_format
            )
            
            # Update the name if we generated a custom number
            # If quotation_number is None, it means no custom format is configured,
            # so we let Odoo handle the default numbering (don't override the name)
            if quotation_number:
                self.write({'name': quotation_number})
                _logger.info(f"Generated custom quotation number: {quotation_number} (AMC format: {use_amc_format}, Estimation: {bool(self.estimation_id)})")
            else:
                _logger.info(f"No custom format configured - using Odoo default numbering (AMC format: {use_amc_format}, Estimation: {bool(self.estimation_id)})")
        elif not format_configured:
            # No custom format configured, let Odoo handle default numbering
            _logger.info(f"No custom format configured in Quotation Configuration - using Odoo default numbering")
        
        # Move to Pending Approval stage
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
        """Decline quotation and return to Draft stage with reason"""
        # Open a wizard to capture decline reason
        return {
            'name': 'Decline Quotation',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.quotation.decline.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
            }
        }
    
    def action_reject_confirm(self, reason=''):
        """Confirm rejection and move quotation to Declined stage"""
        declined_stage = self.env['sale.quotation.stage'].search([('code', '=', 'declined')], limit=1)
        if not declined_stage:
            raise ValidationError("Declined stage not found. Please check stage configuration.")
        self.write({
            'quotation_stage_id': declined_stage.id,
            'decline_reason': reason
        })
        if reason:
            self.message_post(body=f'Quotation declined. Reason: {reason}')
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
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create - quotations remain in draft state without custom number until sent for approval"""
        # Don't generate quotation number at creation - keep default Odoo behavior
        # Quotation number will be generated when "Send for Approval" is clicked
        orders = super().create(vals_list)
        return orders

    def action_mark_printed(self):
        """Mark quotation as printed"""
        if self.quotation_stage_id.code == 'pending_approval':
            self.printed_without_approval = True
        elif self.quotation_stage_id.code == 'quotation':
            # After printing in Approved/Quotation stage, move to Quotation Sent
            sent_stage = self.env['sale.quotation.stage'].search([('code', '=', 'quotation_sent')], limit=1)
            if sent_stage:
                self.write({'quotation_stage_id': sent_stage.id})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    def action_confirm(self):
        """Override Odoo default confirm to update stage after confirmation"""
        # Call parent confirm method (Odoo default)
        result = super(SaleOrder, self).action_confirm()
        
        # After confirmation, move to Sales Order stage
        sales_order_stage = self.env['sale.quotation.stage'].search([('code', '=', 'sales_order')], limit=1)
        if sales_order_stage:
            self.write({'quotation_stage_id': sales_order_stage.id})
        
        return result

