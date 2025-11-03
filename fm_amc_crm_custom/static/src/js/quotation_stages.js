/** @odoo-module **/

import { Component, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";

/**
 * Hide default Odoo buttons when custom quotation stages are active
 */
function hideDefaultButtons() {
    // Wait for DOM to be ready
    setTimeout(() => {
        const form = document.querySelector('.o_form_view[data-model="sale.order"]');
        if (!form) return;
        
        // Check if quotation_stage_id field exists
        const quotationStageField = form.querySelector('[name="quotation_stage_id"]');
        if (!quotationStageField) return;
        
        const header = form.querySelector('header');
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
                // Hide default Confirm button if not in quotation_sent_stage
                if (buttonText === 'Confirm' && buttonName === 'action_confirm') {
                    const quotationSentStage = form.querySelector('[name="is_quotation_sent_stage"]');
                    if (!quotationSentStage || !quotationSentStage.value) {
                        button.style.display = 'none';
                    }
                }
            }
        });
    }, 100);
}

// Run on page load
document.addEventListener('DOMContentLoaded', hideDefaultButtons);

// Also run when Odoo updates the view
const observer = new MutationObserver(() => {
    hideDefaultButtons();
});

// Observe changes to the body
observer.observe(document.body, {
    childList: true,
    subtree: true
});

