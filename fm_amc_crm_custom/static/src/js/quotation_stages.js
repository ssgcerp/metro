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
        
        // Check if quotation stages are enabled by looking for the statusbar
        const statusbar = formElement.querySelector('.o_statusbar_buttons');
        if (!statusbar) return;
        
        // Determine current stage by finding active/highlighted statusbar button
        let currentStage = null;
        const statusbarButtons = statusbar.querySelectorAll('button');
        
        // First, try to find active button by class
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
        
        // If still no stage found, check the hidden input value
        if (!currentStage) {
            const hiddenInput = formElement.querySelector('input[name="quotation_stage_id"][type="hidden"]');
            if (hiddenInput && hiddenInput.value) {
                // Try to match by finding button with matching data attributes
                statusbarButtons.forEach(btn => {
                    const btnText = btn.textContent.trim().toLowerCase();
                    if (btnText.includes('draft')) currentStage = 'draft';
                    else if (btnText.includes('pending') || btnText.includes('approval')) currentStage = 'pending_approval';
                    else if (btnText.includes('quotation') && btnText.includes('sent')) currentStage = 'quotation_sent';
                    else if (btnText.includes('quotation') || btnText.includes('approved')) currentStage = 'quotation';
                    else if (btnText.includes('sales') || btnText.includes('order')) currentStage = 'sales_order';
                    else if (btnText.includes('declined')) currentStage = 'declined';
                    else if (btnText.includes('cancelled')) currentStage = 'cancelled';
                });
            }
        }
        
        // Fallback: if still no stage, assume draft
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

