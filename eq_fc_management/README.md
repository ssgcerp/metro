# Equdai Project Financial Control - Odoo 19 Module

## Overview
This module provides comprehensive project financial control management with automatic project code generation, financial tracking, and visual indicators for cost overruns and profit margins.

## Features
- **Project Configuration**: Set up project numbering formats for AMC and non-AMC projects
- **Automatic Project Code Generation**: Generates unique project codes based on configuration
- **Financial Tracking**: Monitor actual vs estimated costs, profits, and invoice payments
- **Visual Indicators**: Color-coded labels for cost overruns and profit thresholds
- **Branch Management**: Organize projects by branches
- **Compatible**: Works with both Odoo Enterprise and Community editions

## Installation

1. Copy the `eq_fc_management` folder to your Odoo addons directory
2. Update the apps list in Odoo
3. Search for "Equdai Project Financial Control"
4. Click Install

## Usage

### Configuration
1. Navigate to **Financial Control > Project Configuration**
2. Set up numbering formats for AMC and non-AMC projects:
   - Configure prefixes (e.g., "AMC", "PROJ")
   - Set suffixes if needed
   - Define padding digits for sequential numbering
3. Set profit and cost overrun thresholds:
   - Profit Warning Threshold: Percentage below which profit label turns yellow
   - Profit Danger Threshold: Percentage below which profit label turns red
   - Cost Warning Threshold: Percentage above which cost label turns orange
   - Cost Danger Threshold: Percentage above which cost label turns red

### Creating Projects
1. Create a new project in the Project module
2. Enable "Is AMC Project" if it's an AMC project (or leave unchecked for non-AMC)
3. Select the appropriate branch
4. The project code will be automatically generated based on the configuration

### Financial Tracking
1. Open any project form
2. Go to the "Financial Tracking" tab
3. Enter financial information:
   - **Costs**: Estimated and actual costs
   - **Profit**: Estimated and actual profit (calculated automatically)
   - **Invoice Details**: Total invoice amount and paid amount

### Visual Indicators
- **Green**: Within acceptable thresholds
- **Yellow/Orange**: Warning level exceeded
- **Red**: Critical threshold exceeded

## Dependencies
- base
- project
- account
- sale

## Support
For issues or questions, contact Equdai support.

## License
LGPL-3









