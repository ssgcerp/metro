/** @odoo-module **/

import { Component, onMounted, onWillUnmount } from "@odoo/owl";
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

/**
 * Patch FormController to hide default Odoo buttons when custom quotation stages are active
 */
patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.props.resModel === 'sale.order') {
            this._hideDefaultButtonsInterval = setInterval(() => {
                this._hideDefaultButtons();
            }, 500);
        }
    },

    onWillUnmount() {
        super.onWillUnmount?.();
        if (this._hideDefaultButtonsInterval) {
            clearInterval(this._hideDefaultButtonsInterval);
        }
    },

    _hideDefaultButtons() {
        const formElement = document.querySelector('.o_form_view[data-model="sale.order"]');
        if (!formElement) return;
        
        // Check if quotation_stage_id field exists
        const quotationStageField = formElement.querySelector('[name="quotation_stage_id"]');
        if (!quotationStageField) return;
        
        const header = formElement.querySelector('header');
        if (!header) return;
        
        // Get current stage flags
        const isDraftField = formElement.querySelector('[name="is_draft_stage"]');
        const isDraft = isDraftField && isDraftField.value;
        const isPendingApprovalField = formElement.querySelector('[name="is_pending_approval_stage"]');
        const isPendingApproval = isPendingApprovalField && isPendingApprovalField.value;
        const isQuotationStageField = formElement.querySelector('[name="is_quotation_stage"]');
        const isQuotationStage = isQuotationStageField && isQuotationStageField.value;
        const isQuotationSentField = formElement.querySelector('[name="is_quotation_sent_stage"]');
        const isQuotationSent = isQuotationSentField && isQuotationSentField.value;
        const isCancelledField = formElement.querySelector('[name="is_cancelled_stage"]');
        const isCancelled = isCancelledField && isCancelledField.value;
        const isSalesOrderField = formElement.querySelector('[name="is_sales_order_stage"]');
        const isSalesOrder = isSalesOrderField && isSalesOrderField.value;
        
        // Hide all buttons first, then show only the ones for current stage
        const buttons = header.querySelectorAll('button[type="object"]');
        buttons.forEach(button => {
            const buttonName = button.getAttribute('name');
            const buttonText = button.textContent.trim();
            
            // Hide default Odoo buttons
            if (!buttonName || (buttonText === 'Send' || buttonText === 'Print' || buttonText === 'Preview')) {
                button.style.display = 'none';
                return;
            }
            
            // Stage-specific button visibility
            if (isDraft) {
                // In Draft: Only show "Send for Approval" and "Cancel"
                if (buttonName === 'action_send_for_approval' || buttonName === 'action_cancel_quotation') {
                    button.style.display = '';
                } else {
                    button.style.display = 'none';
                }
            } else if (isPendingApproval) {
                // In Pending Approval: Only show "Approve", "Decline", and "Cancel"
                if (buttonName === 'action_approve' || buttonName === 'action_reject' || buttonName === 'action_cancel_quotation') {
                    button.style.display = '';
                } else {
                    button.style.display = 'none';
                }
            } else if (isQuotationStage) {
                // In Quotation: Only show "Send", "Print", and "Reset to Draft"
                if (buttonName === 'action_mark_quotation_sent' || buttonName === 'action_mark_printed' || buttonName === 'action_reset_to_draft') {
                    button.style.display = '';
                } else {
                    button.style.display = 'none';
                }
            } else if (isQuotationSent) {
                // In Quotation Sent: Only show "Confirm", "Cancel", and "Reset to Draft"
                if (buttonName === 'action_confirm' || buttonName === 'action_cancel_quotation' || buttonName === 'action_reset_to_draft') {
                    button.style.display = '';
                } else {
                    button.style.display = 'none';
                }
            } else if (isCancelled) {
                // In Cancelled: Only show "Reset to Draft"
                if (buttonName === 'action_reset_to_draft') {
                    button.style.display = '';
                } else {
                    button.style.display = 'none';
                }
            } else if (isSalesOrder) {
                // In Sales Order: Only show "Reset to Draft" and "Cancel"
                if (buttonName === 'action_reset_to_draft' || buttonName === 'action_cancel_quotation') {
                    button.style.display = '';
                } else {
                    button.style.display = 'none';
                }
            }
        });
    },
});

