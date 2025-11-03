/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { useEffect } from "@odoo/owl";

/**
 * Patch FormController to hide default Odoo buttons when custom quotation stages are active
 */
patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.props.resModel === 'sale.order') {
            useEffect(() => {
                const interval = setInterval(() => {
                    this._hideDefaultButtons();
                }, 300);
                return () => clearInterval(interval);
            });
            
            // Also run on model updates
            if (this.model && this.model.root) {
                useEffect(() => {
                    const updateButtonVisibility = () => {
                        setTimeout(() => this._hideDefaultButtons(), 100);
                    };
                    this.model.root.on('change', updateButtonVisibility);
                    return () => {
                        this.model.root.off('change', updateButtonVisibility);
                    };
                });
            }
        }
    },

    _hideDefaultButtons() {
        const formElement = document.querySelector('.o_form_view[data-model="sale.order"]');
        if (!formElement) return;
        
        // Try to get stage from model first (more reliable)
        let currentStage = null;
        if (this.model && this.model.root) {
            const record = this.model.root;
            if (record.data && record.data.quotation_stage_id) {
                const stageData = record.data.quotation_stage_id;
                if (Array.isArray(stageData) && stageData.length > 1) {
                    // It's a Many2one field: [id, name] or {id, name}
                    const stageName = (typeof stageData[1] === 'string') ? stageData[1] : stageData[1]?.name || '';
                    const stageNameLower = stageName.toLowerCase();
                    if (stageNameLower.includes('draft')) currentStage = 'draft';
                    else if (stageNameLower.includes('pending') || stageNameLower.includes('approval')) currentStage = 'pending_approval';
                    else if (stageNameLower.includes('quotation') && stageNameLower.includes('sent')) currentStage = 'quotation_sent';
                    else if (stageNameLower.includes('quotation') || stageNameLower.includes('approved')) currentStage = 'quotation';
                    else if (stageNameLower.includes('sales') || stageNameLower.includes('order')) currentStage = 'sales_order';
                    else if (stageNameLower.includes('declined')) currentStage = 'declined';
                    else if (stageNameLower.includes('cancelled')) currentStage = 'cancelled';
                }
            }
        }
        
        // Fallback: Check statusbar if model didn't provide stage
        if (!currentStage) {
            const statusbar = formElement.querySelector('.o_statusbar_buttons');
            if (statusbar) {
                const statusbarButtons = statusbar.querySelectorAll('button');
                statusbarButtons.forEach(btn => {
                    if (btn.classList.contains('btn-primary') || btn.classList.contains('active') || btn.getAttribute('aria-pressed') === 'true') {
                        const text = btn.textContent.trim().toLowerCase();
                        if (text.includes('draft')) currentStage = 'draft';
                        else if (text.includes('pending') || text.includes('approval')) currentStage = 'pending_approval';
                        else if (text.includes('quotation') && text.includes('sent')) currentStage = 'quotation_sent';
                        else if (text.includes('quotation') || text.includes('approved')) currentStage = 'quotation';
                        else if (text.includes('sales') || text.includes('order')) currentStage = 'sales_order';
                        else if (text.includes('declined')) currentStage = 'declined';
                        else if (text.includes('cancelled')) currentStage = 'cancelled';
                    }
                });
            }
        }
        
        // Final fallback: assume draft
        if (!currentStage) {
            currentStage = 'draft';
        }
        
        const header = formElement.querySelector('header');
        if (!header) return;
        
        // Get all buttons in header
        const buttons = header.querySelectorAll('button[type="object"]');
        
        buttons.forEach(button => {
            const buttonName = button.getAttribute('name');
            const buttonText = button.textContent.trim();
            
            // Always hide buttons without name attribute or default Odoo buttons
            if (!buttonName) {
                button.style.display = 'none';
                return;
            }
            
            // Hide default Odoo buttons by text (but allow our custom ones)
            if ((buttonText === 'Send' && buttonName !== 'action_send_for_approval' && buttonName !== 'action_mark_quotation_sent') ||
                (buttonText === 'Print' && buttonName !== 'action_mark_printed') ||
                buttonText === 'Preview') {
                button.style.display = 'none';
                return;
            }
            
            // Stage-specific visibility - be very strict
            let shouldShow = false;
            
            switch(currentStage) {
                case 'draft':
                    // ONLY show these two buttons in draft
                    shouldShow = (buttonName === 'action_send_for_approval' || buttonName === 'action_cancel_quotation');
                    break;
                case 'pending_approval':
                    shouldShow = (buttonName === 'action_approve' || buttonName === 'action_reject' || buttonName === 'action_cancel_quotation');
                    break;
                case 'quotation':
                    shouldShow = (buttonName === 'action_mark_quotation_sent' || buttonName === 'action_mark_printed' || buttonName === 'action_reset_to_draft');
                    break;
                case 'quotation_sent':
                    shouldShow = (buttonName === 'action_confirm' || buttonName === 'action_cancel_quotation' || buttonName === 'action_reset_to_draft');
                    break;
                case 'declined':
                case 'cancelled':
                    shouldShow = (buttonName === 'action_reset_to_draft');
                    break;
                case 'sales_order':
                    shouldShow = (buttonName === 'action_reset_to_draft' || buttonName === 'action_cancel_quotation');
                    break;
                default:
                    shouldShow = false;
            }
            
            // Force visibility
            if (shouldShow) {
                button.style.display = '';
                button.style.visibility = 'visible';
                button.removeAttribute('hidden');
            } else {
                button.style.display = 'none';
                button.style.visibility = 'hidden';
            }
        });
        
        // Add data attribute to form for CSS targeting
        formElement.classList.remove('o_draft_stage', 'o_pending_stage', 'o_quotation_stage', 'o_quotation_sent_stage', 'o_sales_order_stage', 'o_cancelled_stage', 'o_declined_stage');
        formElement.classList.add(`o_${currentStage}_stage`);
    },
});

