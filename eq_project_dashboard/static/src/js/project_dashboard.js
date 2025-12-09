/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted, useState, xml } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { useEnv } from "@odoo/owl";

export class ProjectDashboard extends Component {
    static template = xml`
        <div class="project_dashboard_container o_action_manager" style="padding: 20px; min-height: 100vh;">
            <!-- Always show debug info -->
            <div class="alert alert-info" style="margin-bottom: 20px; padding: 15px; background: #d1ecf1; border: 1px solid #bee5eb;">
                <strong>Dashboard Debug Info:</strong><br/>
                Loading: <t t-esc="state.loading ? 'Yes' : 'No'"/> | 
                Error: <t t-esc="state.error || 'None'"/> | 
                Project ID: <t t-esc="state.projectId || 'Not Set'"/> |
                Project Name: <t t-esc="state.projectName || 'Not Set'"/>
            </div>
            
            <t t-if="state.loading">
                <div class="text-center p-5">
                    <i class="fa fa-spinner fa-spin fa-3x"/> 
                    <p>Loading dashboard...</p>
                </div>
            </t>
            <t t-elif="state.error">
                <div class="alert alert-danger m-3">
                    <h4>Error Loading Dashboard</h4>
                    <p t-esc="state.error"/>
                    <p t-if="!state.projectId">Project ID not found. Please open this dashboard from a project form.</p>
                    <p><small>Debug info: projectId = <t t-esc="state.projectId || 'null'"/></small></p>
                </div>
            </t>
            <t t-else="">
            <div class="dashboard_header">
                <h1 class="project_name" t-esc="state.projectName || 'Project Dashboard'"/>
                <span class="project_stage" t-esc="state.data?.stage_name || 'No Stage'"/>
            </div>

            <div class="dashboard_tabs">
                <button class="tab_button" t-att-class="{'active': activeTab.value === 'overview'}" t-on-click="() => this.setActiveTab('overview')">
                    <i class="fa fa-dashboard"/> Overview
                </button>
                <button class="tab_button" t-att-class="{'active': activeTab.value === 'estimates'}" t-on-click="() => this.openTabAction('sale.action_orders', '[(\'project_id\', \'=\', ' + state.projectId + ')]')">
                    <i class="fa fa-file-text"/> Estimates
                </button>
                <button class="tab_button" t-att-class="{'active': activeTab.value === 'invoices'}" t-on-click="() => this.openTabAction('account.action_move_out_invoice_type', '[(\'project_id\', \'=\', ' + state.projectId + ')]')">
                    <i class="fa fa-file-invoice"/> Invoices
                </button>
                <button class="tab_button" t-att-class="{'active': activeTab.value === 'expenses'}" t-on-click="() => this.openTabAction('hr_expense.action_hr_expense_sheet_my_all', '[(\'project_id\', \'=\', ' + state.projectId + ')]')">
                    <i class="fa fa-money-bill"/> Expenses
                </button>
                <button class="tab_button" t-att-class="{'active': activeTab.value === 'purchases'}" t-on-click="() => this.openTabAction('purchase.action_purchase_order_form', '[(\'project_id\', \'=\', ' + state.projectId + ')]')">
                    <i class="fa fa-shopping-cart"/> Purchases
                </button>
                <button class="tab_button" t-att-class="{'active': activeTab.value === 'timesheets'}" t-on-click="() => this.openTabAction('hr_timesheet.action_hr_timesheet_line_tree', '[(\'project_id\', \'=\', ' + state.projectId + ')]')">
                    <i class="fa fa-clock"/> Timesheets
                </button>
                <button class="tab_button" t-att-class="{'active': activeTab.value === 'warehouse'}" t-on-click="() => this.openTabAction('stock.action_picking_tree_all', '[(\'project_id\', \'=\', ' + state.projectId + ')]')">
                    <i class="fa fa-warehouse"/> Warehouse
                </button>
            </div>

            <div class="dashboard_content" t-if="activeTab.value === 'overview'">
                <div class="kpi_row">
                    <div class="kpi_card invoice-total">
                        <div class="kpi_label">Invoice Total</div>
                        <div class="kpi_value" t-esc="formatCurrency(state.data?.invoice_total || 0)"/>
                    </div>
                    <div class="kpi_card invoice-paid">
                        <div class="kpi_label">Invoice Paid</div>
                        <div class="kpi_value" t-esc="formatCurrency(state.data?.invoice_paid || 0)"/>
                    </div>
                    <div class="kpi_card invoice-pending">
                        <div class="kpi_label">Invoice Pending</div>
                        <div class="kpi_value" t-esc="formatCurrency(state.data?.invoice_pending || 0)"/>
                    </div>
                </div>

                <div class="kpi_row">
                    <div class="kpi_card estimated">
                        <div class="kpi_label">Estimated Cost</div>
                        <div class="kpi_value" t-esc="formatCurrency(state.data?.estimated_cost || 0)"/>
                    </div>
                    <div class="kpi_card actual">
                        <div class="kpi_label">Actual Cost</div>
                        <div class="kpi_value" t-esc="formatCurrency(state.data?.actual_cost || 0)"/>
                    </div>
                    <div class="kpi_card actual">
                        <div class="kpi_label">Cost Overrun</div>
                        <div class="kpi_value" t-esc="formatCurrency(state.data?.cost_overrun || 0)"/>
                    </div>
                    <div class="kpi_card actual">
                        <div class="kpi_label">Cost Overrun %</div>
                        <div class="kpi_value" t-esc="(state.data?.cost_overrun_pct || 0).toFixed(2) + '%'"/>
                    </div>
                </div>

                <div class="kpi_row">
                    <div class="kpi_card profit">
                        <div class="kpi_label">Estimated Profit</div>
                        <div class="kpi_value" t-esc="formatCurrency(state.data?.estimated_profit || 0)"/>
                    </div>
                    <div class="kpi_card profit">
                        <div class="kpi_label">Actual Profit</div>
                        <div class="kpi_value" t-esc="formatCurrency(state.data?.actual_profit || 0)"/>
                    </div>
                    <div class="kpi_card profit">
                        <div class="kpi_label">Profit %</div>
                        <div class="kpi_value" t-esc="(state.data?.profit_percentage || 0).toFixed(2) + '%'"/>
                    </div>
                    <div class="kpi_card estimated">
                        <div class="kpi_label">Project Stage</div>
                        <div class="kpi_value" t-esc="state.data?.stage_name || '-'"/>
                    </div>
                </div>

                <div class="charts_row">
                    <div class="chart_card">
                        <h3>Invoice Status</h3>
                        <canvas id="invoice_chart" t-ref="invoiceChart"/>
                    </div>
                    <div class="chart_card">
                        <h3>Cost Comparison</h3>
                        <canvas id="cost_chart" t-ref="costChart"/>
                    </div>
                </div>
            </div>
            </t>
        </div>
    `;

    setup() {
        this.env = useEnv();
        this.actionService = useService("action");
        
        // Debug: Log everything to understand structure
        console.log("=== ProjectDashboard Setup ===");
        console.log("Full props:", this.props);
        console.log("Props.action:", this.props.action);
        console.log("Props.context:", this.props.context);
        
        // Try multiple ways to get project_id
        const action = this.props.action || {};
        const context = action.context || this.props.context || {};
        
        // Get project_id - try multiple locations
        let projectId = context.project_id || 
                       action.resId ||
                       (action.res_id ? parseInt(action.res_id) : null) ||
                       null;
        
        // Convert to integer if it's a string
        if (projectId && typeof projectId === 'string') {
            projectId = parseInt(projectId);
        }
        
        const projectName = context.project_name || 
                           action.name || 
                           action.display_name ||
                           'Project Dashboard';
        
        console.log("Extracted - projectId:", projectId, "projectName:", projectName);
        
        this.state = useState({
            loading: true,
            projectId: projectId,
            projectName: projectName,
            data: null,
            error: null,
        });
        
        this.activeTab = useState({ value: 'overview' });
        this.invoiceChart = null;
        this.costChart = null;
        
        onWillStart(async () => {
            console.log("onWillStart - projectId:", this.state.projectId);
            if (this.state.projectId) {
                await this.loadDashboardData();
            } else {
                console.error("No project_id found. Full props:", this.props);
                this.state.error = "Project ID not found. Please open this dashboard from a project form.";
                this.state.loading = false;
            }
        });
        
        onMounted(() => {
            console.log("onMounted - data:", this.state.data);
            if (this.state.data) {
                setTimeout(() => this.renderCharts(), 200);
            }
        });
    }
    
    formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value);
    }
    
    setActiveTab(tab) {
        this.activeTab.value = tab;
        if (tab === 'overview') {
            setTimeout(() => this.renderCharts(), 100);
        }
    }
    
    async openTabAction(actionName, domainStr) {
        try {
            // Replace placeholder with actual project ID
            const finalDomainStr = domainStr.replace(/project_id/g, this.state.projectId.toString());
            
            // Parse domain string
            let domain;
            try {
                domain = JSON.parse(finalDomainStr.replace(/'/g, '"'));
            } catch (e) {
                // If parsing fails, create a simple domain
                domain = [['project_id', '=', this.state.projectId]];
            }
            
            this.actionService.doAction(actionName, {
                additionalContext: {
                    default_project_id: this.state.projectId,
                },
                domain: domain,
            });
        } catch (error) {
            console.error("Error opening tab action:", error);
            // Fallback: try with simple domain
            this.actionService.doAction(actionName, {
                additionalContext: {
                    default_project_id: this.state.projectId,
                },
                domain: [['project_id', '=', this.state.projectId]],
            });
        }
    }
    
    async loadDashboardData() {
        if (!this.state.projectId) {
            console.error("loadDashboardData: Project ID not found");
            this.state.error = "Project ID not found";
            this.state.loading = false;
            return;
        }
        
        console.log("loadDashboardData: Fetching data for project_id:", this.state.projectId);
        
        try {
            const result = await rpc("/project/dashboard/" + this.state.projectId, {});
            console.log("loadDashboardData: RPC result:", result);
            
            if (result && result.status === 'success') {
                this.state.data = result.data;
                this.state.error = null;
                console.log("loadDashboardData: Data loaded successfully:", this.state.data);
                setTimeout(() => this.renderCharts(), 100);
            } else {
                const errorMsg = result?.message || "Failed to load dashboard data";
                console.error("loadDashboardData: Error response:", result);
                this.state.error = errorMsg;
            }
        } catch (error) {
            console.error("loadDashboardData: Exception caught:", error);
            this.state.error = error.message || "Failed to load dashboard data. Please check the server logs.";
        } finally {
            this.state.loading = false;
            console.log("loadDashboardData: Finished. Loading:", this.state.loading, "Error:", this.state.error);
        }
    }
    
    renderCharts() {
        if (!this.state.data) return;
        
        const data = this.state.data;
        
        // Destroy existing charts if they exist
        if (this.invoiceChart) {
            this.invoiceChart.destroy();
            this.invoiceChart = null;
        }
        if (this.costChart) {
            this.costChart.destroy();
            this.costChart = null;
        }
        
        // Wait for Chart.js to be available - load dynamically
        if (typeof Chart === 'undefined') {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
            script.onload = () => {
                setTimeout(() => this.renderCharts(), 100);
            };
            document.head.appendChild(script);
            return;
        }
        
        // Get the root element
        const rootEl = document.querySelector('.project_dashboard_container');
        if (!rootEl) {
            setTimeout(() => this.renderCharts(), 100);
            return;
        }
        
        // Render Invoice Pie Chart
        const invoiceCanvas = rootEl.querySelector('#invoice_chart');
        if (invoiceCanvas && !this.invoiceChart) {
            const ctx = invoiceCanvas.getContext('2d');
            this.invoiceChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: data.chart_invoice_labels || [],
                    datasets: [{
                        data: data.chart_invoice_values || [],
                        backgroundColor: ['#27ae60', '#f39c12'],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.parsed || 0;
                                    return label + ': $' + value.toLocaleString('en-US', {minimumFractionDigits: 2});
                                }
                            }
                        }
                    }
                }
            });
        }
        
        // Render Cost Bar Chart
        const costCanvas = rootEl.querySelector('#cost_chart');
        if (costCanvas && !this.costChart) {
            const ctx = costCanvas.getContext('2d');
            this.costChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.chart_cost_labels || [],
                    datasets: [{
                        label: 'Cost',
                        data: data.chart_cost_values || [],
                        backgroundColor: ['#c0392b', '#8e44ad'],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const value = context.parsed.y || 0;
                                    return '$' + value.toLocaleString('en-US', {minimumFractionDigits: 2});
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toLocaleString('en-US');
                                }
                            }
                        }
                    }
                }
            });
        }
    }
}

// Register as client action
ProjectDashboard.props = ["*"];

// Ensure component is registered correctly
registry.category("actions").add("project_dashboard", ProjectDashboard);

// Debug: Verify registration
console.log("ProjectDashboard registered:", registry.category("actions").get("project_dashboard"));
console.log("ProjectDashboard class:", ProjectDashboard);
console.log("ProjectDashboard template:", ProjectDashboard.template);

