# EQ Project Dashboard Module

## Overview
This module adds a comprehensive dashboard button to Odoo 19 Enterprise projects, providing real-time KPIs, interactive charts, and quick navigation to related records.

## Features

### Dashboard Button
- Smart button added to project form view
- Icon: `fa-bar-chart`
- Opens custom dashboard for the selected project

### Dashboard KPIs
The dashboard displays three rows of KPIs:

**Row 1 - Invoices:**
- Invoice Total
- Invoice Paid
- Invoice Pending

**Row 2 - Costs:**
- Estimated Cost
- Actual Cost
- Cost Overrun
- Cost Overrun %

**Row 3 - Profits:**
- Estimated Profit
- Actual Profit
- Profit %
- Project Stage

### Charts
- **Pie Chart**: Invoice Paid vs Pending
- **Bar Chart**: Actual Cost vs Estimated Cost

### Navigation Tabs
Quick access to filtered views:
- **Estimates**: Sale Orders filtered by project
- **Invoices**: Account Moves filtered by project
- **Expenses**: HR Expenses filtered by project
- **Purchases**: Purchase Orders filtered by project
- **Timesheets**: Analytic Lines filtered by project
- **Warehouse**: Stock Pickings filtered by project

## Installation

1. Copy the `eq_project_dashboard` folder to your Odoo addons directory
2. Update the apps list in Odoo
3. Install the module "EQ Project Dashboard"

## Dependencies

- `project`
- `sale_management`
- `account`
- `purchase`
- `hr_expense`
- `stock`
- `analytic`
- `web`

## Technical Details

### Models
- `project.dashboard.helper`: Helper model for computing dashboard values
- Extends `project.project` with `action_open_project_dashboard` method

### Controller
- Route: `/project/dashboard/<project_id>`
- Returns JSON with dashboard KPIs and chart data

### JavaScript
- OWL Component: `ProjectDashboard`
- Uses Chart.js for rendering charts
- Dynamically loads Chart.js from CDN if not available

### Security
- Project Managers: Full access
- Project Users: Read-only access
- Administrators: Full access

## Usage

1. Open any project form
2. Click the "Dashboard" smart button
3. View KPIs and charts on the overview tab
4. Click navigation tabs to view filtered records

## Customization

### KPI Colors
Colors are defined in `dashboard_style.scss`:
- Invoice Total: `#4b77be`
- Invoice Paid: `#27ae60`
- Invoice Pending: `#f39c12`
- Estimated: `#8e44ad`
- Actual: `#c0392b`
- Profit: `#2ecc71`

### Chart Configuration
Charts are configured in `project_dashboard.js`. Modify the Chart.js options to customize appearance and behavior.

## Notes

- The module requires projects to have analytic accounts for accurate cost tracking
- Invoice calculations use analytic distribution or sale order links
- Cost calculations aggregate from analytic lines, purchase orders, and expenses
- Chart.js is loaded dynamically from CDN

## Support

For issues or questions, contact the development team.

## License

LGPL-3

