/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { Menu } from "@web/webclient/menu/menu";

// Apply section header styles
function applySectionHeaderStyles() {
    const sectionMenuIds = [
        'menu_amc_settings_section_contracts',
        'menu_amc_settings_section_estimations'
    ];
    
    sectionMenuIds.forEach(menuId => {
        const menuItem = document.querySelector(`li[data-menu-id="${menuId}"]`) ||
                        document.querySelector(`a[data-menu-id="${menuId}"]`)?.closest('li');
        
        if (menuItem && !menuItem.classList.contains('dropdown-header')) {
            menuItem.classList.add('dropdown-menu_group', 'dropdown-header');
            menuItem.style.paddingLeft = '20px';
        }
    });
}

// Patch Menu to apply styles after rendering
patch(Menu.prototype, {
    setup() {
        super.setup();
    },
    
    async onMounted() {
        await super.onMounted?.();
        setTimeout(applySectionHeaderStyles, 0);
    },
});

// Use mutation observer for dynamic menu updates
const observer = new MutationObserver(() => {
    applySectionHeaderStyles();
});

// Start observing when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        observer.observe(document.body, { childList: true, subtree: true });
        applySectionHeaderStyles();
    });
} else {
    observer.observe(document.body, { childList: true, subtree: true });
    applySectionHeaderStyles();
}

