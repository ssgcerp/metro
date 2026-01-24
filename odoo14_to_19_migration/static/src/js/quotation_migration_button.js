/** @odoo-module **/

console.log("🚀 quotation_migration_button.js LOADED!");

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";

patch(ListController.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        
        // Check if this is the quotation migration list view
        if (this.props.resModel === 'eq.migration.quotation') {
            console.log("✅ Quotation migration list view detected, will add upload button");
        }
    },
    
    async onWillStart() {
        const result = super.onWillStart ? await super.onWillStart() : Promise.resolve();
        // Check if this is the quotation migration list view
        if (this.props.resModel === 'eq.migration.quotation') {
            // Wait a bit for DOM to render
            setTimeout(() => this.addUploadButton(), 300);
        }
        return result;
    },
    
    addUploadButton() {
        // Check if button already exists
        if (document.getElementById('quotation_upload_excel_btn')) {
            console.log("Button already exists, skipping");
            return;
        }
        
        // Find the control panel buttons area
        let controlPanel = document.querySelector('.o_control_panel');
        if (!controlPanel) {
            console.log("Control panel not found, retrying...");
            setTimeout(() => this.addUploadButton(), 500);
            return;
        }
        
        // Find the buttons container - try multiple selectors for Odoo 19
        let buttonsArea = controlPanel.querySelector('.o_cp_left') ||
                         controlPanel.querySelector('.o_control_panel_main_buttons') ||
                         controlPanel.querySelector('.o_cp_main') ||
                         controlPanel.querySelector('.o_control_panel_main') ||
                         controlPanel.querySelector('.o_control_panel_breadcrumbs')?.parentElement;
        
        if (!buttonsArea) {
            console.log("Buttons area not found, retrying...");
            setTimeout(() => this.addUploadButton(), 500);
            return;
        }
        
        console.log("Found buttons area, adding upload button");
        
        // Create button container if needed
        let buttonContainer = buttonsArea.querySelector('.o_quotation_upload_buttons');
        if (!buttonContainer) {
            buttonContainer = document.createElement('div');
            buttonContainer.className = 'o_quotation_upload_buttons';
            buttonContainer.style.display = 'inline-flex';
            buttonContainer.style.alignItems = 'center';
            buttonContainer.style.marginLeft = '10px';
            
            // Try to insert after title/breadcrumbs
            const title = buttonsArea.querySelector('.o_control_panel_breadcrumbs') ||
                         buttonsArea.querySelector('h1') ||
                         buttonsArea.querySelector('.o_cp_searchview') ||
                         buttonsArea.firstChild;
            if (title && title.parentNode) {
                title.parentNode.insertBefore(buttonContainer, title.nextSibling);
            } else {
                buttonsArea.insertBefore(buttonContainer, buttonsArea.firstChild);
            }
        }
        
        // Create "Upload Excel" button
        const uploadButton = document.createElement('button');
        uploadButton.id = 'quotation_upload_excel_btn';
        uploadButton.type = 'button';
        uploadButton.className = 'btn btn-primary';
        uploadButton.innerHTML = '<i class="fa fa-upload"></i> Upload Excel';
        uploadButton.style.marginRight = '5px';
        
        // Add click handler for Upload Excel
        uploadButton.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log("Upload Excel button clicked");
            try {
                const action = await this.orm.call(
                    'eq.migration.quotation',
                    'action_open_upload_wizard',
                    [],
                    {}
                );
                if (action) {
                    this.action.doAction(action);
                }
            } catch (error) {
                console.error('Error opening upload wizard:', error);
            }
        });
        
        buttonContainer.appendChild(uploadButton);
        
        // Create "Add Excel" button
        const addButton = document.createElement('button');
        addButton.id = 'quotation_add_excel_btn';
        addButton.type = 'button';
        addButton.className = 'btn btn-primary';
        addButton.innerHTML = '<i class="fa fa-plus"></i> Add Excel';
        addButton.style.marginRight = '5px';
        
        // Add click handler for Add Excel
        addButton.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log("Add Excel button clicked");
            try {
                const action = await this.orm.call(
                    'eq.migration.quotation',
                    'action_open_upload_wizard',
                    [],
                    {}
                );
                if (action) {
                    this.action.doAction(action);
                }
            } catch (error) {
                console.error('Error opening upload wizard:', error);
            }
        });
        
        buttonContainer.appendChild(addButton);
        console.log("✅ Upload Excel and Add Excel buttons added successfully");
    },
});
