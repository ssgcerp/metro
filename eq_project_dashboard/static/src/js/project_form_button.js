/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// Patch the project form to add dashboard button dynamically
patch(FormController.prototype, {
    setup() {
        super.setup();
        if (this.props.resModel === 'project.project') {
            this.actionService = useService("action");
            onMounted(() => {
                setTimeout(() => this.addDashboardButton(), 1000);
            });
        }
    },
    
    addDashboardButton() {
        const formView = document.querySelector('.o_form_view');
        if (!formView) return;
        
        let buttonBox = formView.querySelector('.oe_button_box');
        if (!buttonBox) {
            // Create button_box if it doesn't exist
            const sheet = formView.querySelector('.o_form_sheet');
            if (sheet) {
                buttonBox = document.createElement('div');
                buttonBox.className = 'oe_button_box';
                sheet.insertBefore(buttonBox, sheet.firstChild);
            } else {
                return;
            }
        }
        
        // Check if button already exists
        if (buttonBox.querySelector('.dashboard_button')) {
            return;
        }
        
        const projectId = this.props.resId;
        if (!projectId) return;
        
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'oe_stat_button dashboard_button';
        button.innerHTML = `
            <i class="fa fa-bar-chart"></i>
            <div class="o_stat_info">
                <span class="o_stat_text">Dashboard</span>
            </div>
        `;
        button.onclick = () => {
            this.actionService.doAction({
                type: 'ir.actions.client',
                tag: 'project_dashboard',
                context: {
                    project_id: projectId,
                    project_name: this.props.record?.data?.name || '',
                },
                target: 'current',
            });
        };
        buttonBox.appendChild(button);
    },
});

