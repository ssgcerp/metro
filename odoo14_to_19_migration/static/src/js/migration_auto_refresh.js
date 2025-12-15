/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

patch(FormController.prototype, {
    setup() {
        super.setup();
        this.migrationRefreshInterval = null;
        this.autoContinueTimeout = null;
        this.autoContinueCheckDone = false;
    },

    async onWillStart() {
        await super.onWillStart();
        this._startMigrationAutoRefresh();
        this._checkAutoContinue();
    },

    async _checkAutoContinue() {
        // Check if migration is in progress and should auto-continue
        // Only check once per view load to avoid infinite loops
        if (this.autoContinueCheckDone) {
            return;
        }
        
        const record = this.model.root;
        if (!record || !record.data) {
            return;
        }
        
        // Check if migration is in progress
        const isMigrating = record.data.is_migrating;
        console.log('Auto-continue check - is_migrating:', isMigrating);
        
        if (isMigrating) {
            // Determine which migration type (quotations or employees)
            let migrated = 0;
            let total = 0;
            let actionMethod = null;
            
            // Check for quotation migration
            if (record.data.quotations_migrated !== undefined) {
                migrated = record.data.quotations_migrated || 0;
                total = record.data.quotations_count || 0;
                actionMethod = 'action_migrate_quotations';
            }
            // Check for employee migration
            else if (record.data.employees_migrated !== undefined) {
                migrated = record.data.employees_migrated || 0;
                total = record.data.employees_count || 0;
                actionMethod = 'action_migrate_employees';
            }
            
            console.log(`Migration state - migrated: ${migrated}, total: ${total}, method: ${actionMethod}`);
            
            if (migrated < total && actionMethod) {
                this.autoContinueCheckDone = true;
                console.log(`Auto-continuing ${actionMethod}: ${migrated}/${total} migrated`);
                // Wait a moment for view to load, then continue migration
                this.autoContinueTimeout = setTimeout(async () => {
                    try {
                        // Trigger migration again (server will continue from current offset)
                        const orm = this.env.services.orm;
                        console.log(`Calling ${actionMethod} to continue migration...`);
                        await orm.call(
                            record.resModel,
                            actionMethod,
                            [[record.resId]],
                        );
                        console.log(`${actionMethod} completed, will check again on next view reload`);
                        // Reset flag after a delay so the next view reload can continue if needed
                        setTimeout(() => {
                            this.autoContinueCheckDone = false;
                        }, 1000);
                    } catch (error) {
                        console.error('Error auto-continuing migration:', error);
                        // Reset flag on error so user can retry
                        this.autoContinueCheckDone = false;
                    }
                }, 1500); // Wait 1.5 seconds before continuing (reduced from 2s)
            } else if (migrated >= total && actionMethod) {
                console.log(`Migration complete: ${migrated}/${total}`);
            } else if (!actionMethod) {
                console.warn('Migration in progress but could not determine migration type');
            }
        }
    },

    _startMigrationAutoRefresh() {
        const record = this.model.root;
        
        if (record && record.data && record.data.is_migrating) {
            // Clear any existing interval
            if (this.migrationRefreshInterval) {
                clearInterval(this.migrationRefreshInterval);
            }
            
            // Refresh every 1 second when migration is in progress (simple reload)
            this.migrationRefreshInterval = setInterval(async () => {
                try {
                    const currentRecord = this.model.root;
                    if (currentRecord && currentRecord.data && currentRecord.data.is_migrating) {
                        // Reload the record to get updated counts
                        await currentRecord.load();
                        
                        // Trigger auto-continue countdown restart if countdown_seconds changed
                        // This ensures countdown restarts after each batch
                        const countdownSeconds = currentRecord.data.countdown_seconds || 0;
                        const autoContinue = currentRecord.data.auto_continue;
                        
                        if (autoContinue && countdownSeconds > 0) {
                            // Dispatch custom event to trigger countdown restart
                            console.log("🔄 Refresh interval detected countdown restart needed");
                            const event = new CustomEvent('migration_countdown_restart', {
                                detail: { seconds: countdownSeconds }
                            });
                            document.dispatchEvent(event);
                        }
                        
                        // Log progress to console for debugging
                        // Check for quotation or employee migration
                        let migrated = 0;
                        let total = 0;
                        let migrationType = 'Unknown';
                        let actionMethod = null;
                        
                        if (currentRecord.data.quotations_migrated !== undefined) {
                            migrated = currentRecord.data.quotations_migrated || 0;
                            total = currentRecord.data.quotations_count || 0;
                            migrationType = 'Quotations';
                            actionMethod = 'action_migrate_quotations';
                        } else if (currentRecord.data.employees_migrated !== undefined) {
                            migrated = currentRecord.data.employees_migrated || 0;
                            total = currentRecord.data.employees_count || 0;
                            migrationType = 'Employees';
                            actionMethod = 'action_migrate_employees';
                        }
                        
                        const progress = total > 0 ? (migrated / total * 100) : 0;
                        console.log(`${migrationType} Migration Progress: ${migrated}/${total} (${progress.toFixed(1)}%)`);
                        
                        // Check if countdown is active - if so, don't auto-continue (let countdown handle it)
                        
                        // Only auto-continue if countdown is not active and migration is in progress
                        if (migrated < total && actionMethod && !this.autoContinueCheckDone && !autoContinue && currentRecord.data.is_migrating) {
                            console.log(`Auto-continuing ${actionMethod} from refresh interval (no countdown active)...`);
                            this.autoContinueCheckDone = true;
                            
                            // Trigger migration again after a short delay
                            setTimeout(async () => {
                                try {
                                    const orm = this.env.services.orm;
                                    console.log(`Calling ${actionMethod} from refresh interval...`);
                                    await orm.call(
                                        currentRecord.resModel,
                                        actionMethod,
                                        [[currentRecord.resId]],
                                    );
                                    console.log(`${actionMethod} completed from refresh interval`);
                                    // Reset flag so it can continue on next check
                                    this.autoContinueCheckDone = false;
                                } catch (error) {
                                    console.error('Error auto-continuing migration from refresh:', error);
                                    this.autoContinueCheckDone = false;
                                }
                            }, 1500); // Wait 1.5 seconds before continuing
                        } else if (migrated >= total) {
                            console.log(`${migrationType} Migration complete: ${migrated}/${total}`);
                            // Stop refresh when complete
                            if (this.migrationRefreshInterval) {
                                clearInterval(this.migrationRefreshInterval);
                                this.migrationRefreshInterval = null;
                            }
                        } else if (autoContinue && countdownSeconds > 0) {
                            console.log(`Countdown active (${countdownSeconds}s), waiting for countdown to trigger...`);
                        }
                    } else {
                        // Stop refresh if migration is not in progress
                        if (this.migrationRefreshInterval) {
                            clearInterval(this.migrationRefreshInterval);
                            this.migrationRefreshInterval = null;
                        }
                    }
                } catch (error) {
                    console.error('Error refreshing migration progress:', error);
                }
            }, 1000); // Refresh every 1 second
        } else {
            // Stop refresh if migration is not in progress
            if (this.migrationRefreshInterval) {
                clearInterval(this.migrationRefreshInterval);
                this.migrationRefreshInterval = null;
            }
        }
    },

    onWillUnmount() {
        super.onWillUnmount();
        if (this.migrationRefreshInterval) {
            clearInterval(this.migrationRefreshInterval);
            this.migrationRefreshInterval = null;
        }
        if (this.autoContinueTimeout) {
            clearTimeout(this.autoContinueTimeout);
            this.autoContinueTimeout = null;
        }
        this.autoContinueCheckDone = false;
    },
});
