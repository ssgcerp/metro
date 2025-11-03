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
        
        // List of our custom button names
        const customButtons = [
            'action_send_for_approval',
            'action_cancel_quotation',
            'action_approve',
            'action_reject',
            'action_mark_quotation_sent',
            'action_mark_printed',
            'action_reset_to_draft',
            'action_confirm'
        ];
        
        // Hide buttons that are not our custom buttons
        const buttons = header.querySelectorAll('button[type="object"]');
        buttons.forEach(button => {
            const buttonName = button.getAttribute('name');
            if (buttonName && !customButtons.includes(buttonName)) {
                // Check button text to identify default Odoo buttons
                const buttonText = button.textContent.trim();
                if (['Send', 'Print', 'Preview'].includes(buttonText)) {
                    button.style.display = 'none';
                }
            } else if (buttonName === 'action_confirm' && customButtons.includes(buttonName)) {
                // Check if we should show our Confirm button (only in quotation_sent_stage)
                const isQuotationSentField = formElement.querySelector('[name="is_quotation_sent_stage"]');
                const isQuotationSent = isQuotationSentField && isQuotationSentField.value;
                // Only show Confirm if in quotation_sent_stage
                if (!isQuotationSent) {
                    button.style.display = 'none';
                }
            }
        });
    },
});

