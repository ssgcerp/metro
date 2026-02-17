/** @odoo-module **/
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";
import { patch } from "@web/core/utils/patch";

patch(AccountReportFilters.prototype, {
    get selectedSpecificCompanyName() {
        const filters = this.controller.cachedFilterOptions.specific_company_filter;
        if (!filters) return "";
        const selected = filters.find(f => f.selected);
        return selected ? selected.name : "All Companies";
    },

    async selectSpecificCompany(companyId) {
        if (companyId === 'all') companyId = null;
        await this.controller.updateOption('specific_company_id', companyId);
        await this.controller.reload('specific_company_id', this.controller.cachedFilterOptions);
    }
});
