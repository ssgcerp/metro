/** @odoo-module **/

// DEBUG: Verify this file is loaded
console.log("🚀 migration_auto_continue.js LOADED!");

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

patch(FormController.prototype, {
    setup() {
        super.setup();
        this.autoContinueTimeout = null;
        this.autoContinueCheckDone = false;
        this.autoContinueInterval = null;
    },

    async onWillStart() {
        await super.onWillStart();
        // Check after a delay to ensure data is loaded
        setTimeout(() => this._checkAutoContinue(), 500);
    },

    onWillUpdateProps(nextProps) {
        super.onWillUpdateProps(nextProps);
        // Reset flag when props update (form reloaded)
        this.autoContinueCheckDone = false;
        // Check again after props update
        setTimeout(() => this._checkAutoContinue(), 500);
    },

    async _checkAutoContinue() {
        // Prevent multiple simultaneous checks
        if (this.autoContinueCheckDone) {
            return;
        }
        
        try {
            const record = this.model.root;
            if (!record || !record.data) {
                console.log('⚠️ No record data available yet');
                return;
            }
            
            // Check if migration is in progress
            const isMigrating = record.data.is_migrating;
            const migrated = record.data.quotations_migrated || 0;
            const total = record.data.quotations_count || 0;
            
            console.log(`🔍 Auto-continue check - is_migrating: ${isMigrating}, migrated: ${migrated}/${total}`);
            
            if (isMigrating && migrated < total) {
                this.autoContinueCheckDone = true;
                console.log(`🔄 Auto-continuing migration: ${migrated}/${total} migrated`);
                
                // Wait a moment for view to fully load, then continue migration
                this.autoContinueTimeout = setTimeout(async () => {
                    try {
                        const orm = this.env.services.orm;
                        const resModel = record.resModel;
                        const resId = record.resId;
                        
                        console.log(`📞 Calling action_continue_migration_auto for ${resModel} (ID: ${resId})...`);
                        
                        await orm.call(
                            resModel,
                            'action_continue_migration_auto',
                            [[resId]],
                        );
                        
                        console.log(`✅ action_continue_migration_auto completed, form will reload automatically`);
                        
                        // Reset flag after a delay so the next view reload can continue
                        setTimeout(() => {
                            this.autoContinueCheckDone = false;
                        }, 1000);
                    } catch (error) {
                        console.error('❌ Error auto-continuing migration:', error);
                        // Reset flag on error so user can retry
                        this.autoContinueCheckDone = false;
                    }
                }, 1500); // Wait 1.5 seconds before continuing
            } else if (migrated >= total && isMigrating) {
                console.log(`✅ Migration complete: ${migrated}/${total}`);
                this.autoContinueCheckDone = true; // Don't continue if complete
            }
        } catch (error) {
            console.error('❌ Error in _checkAutoContinue:', error);
            this.autoContinueCheckDone = false;
        }
    },

    // Also set up an interval to check periodically when migration is active
    async onMounted() {
        await super.onMounted();
        
        // Set up periodic check every 2 seconds when migration is active
        this.autoContinueInterval = setInterval(() => {
            const record = this.model.root;
            if (record && record.data && record.data.is_migrating) {
                const migrated = record.data.quotations_migrated || 0;
                const total = record.data.quotations_count || 0;
                
                // Only check if not already processing and migration is incomplete
                if (!this.autoContinueCheckDone && migrated < total) {
                    console.log(`⏰ Periodic check: ${migrated}/${total} - triggering auto-continue`);
                    this._checkAutoContinue();
                }
            } else {
                // Stop interval if migration is not active
                if (this.autoContinueInterval) {
                    clearInterval(this.autoContinueInterval);
                    this.autoContinueInterval = null;
                }
            }
        }, 2000); // Check every 2 seconds
    },

    onWillUnmount() {
        super.onWillUnmount();
        if (this.autoContinueTimeout) {
            clearTimeout(this.autoContinueTimeout);
            this.autoContinueTimeout = null;
        }
        if (this.autoContinueInterval) {
            clearInterval(this.autoContinueInterval);
            this.autoContinueInterval = null;
        }
        this.autoContinueCheckDone = false;
    },
});
