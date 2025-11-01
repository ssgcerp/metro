/** @odoo-module **/

/** 
 * equdai_theme: Company Logo Switch
 * Safely replaces the company logo in the top-left navbar
 */

export function replaceCompanyLogo() {
    // Wait until navbar is loaded
    const navbarInterval = setInterval(() => {
        const $logo = document.querySelector('.o_main_navbar .o_company_logo');
        if ($logo) {
            clearInterval(navbarInterval);

            // Replace the logo src
            $logo.src = '/equdai_theme/static/src/img/company_logo.png';
            $logo.alt = 'Company';

            // Optional: adjust height if needed
            $logo.style.maxHeight = '50px';
        }
    }, 100); // check every 100ms
}

// Run after DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    replaceCompanyLogo();
});
