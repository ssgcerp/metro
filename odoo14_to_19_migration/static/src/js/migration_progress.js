/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

export class MigrationProgressWidget extends Component {
    setup() {
        super.setup();
        this.refreshInterval = null;
        this.startAutoRefresh();
    }

    startAutoRefresh() {
        // Check if migration is in progress
        const isMigrating = this.props.record.data.is_migrating;
        
        if (isMigrating) {
            // Auto-refresh every 2 seconds when migration is in progress
            this.refreshInterval = setInterval(() => {
                this.props.record.model.load();
            }, 2000);
        }
    }

    willUnmount() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }
}

MigrationProgressWidget.template = "odoo14_to_19_migration.MigrationProgressWidget";

registry.category("fields").add("migration_progress", MigrationProgressWidget);
