# Equdai Project Financial Control - Installation Guide

## Module Overview
The **eq_fc_management** module provides comprehensive project financial control management for Odoo 19, compatible with both Enterprise and Community editions.

## Features
✅ Project Configuration page under Configuration menu  
✅ Configurable numbering formats for AMC and non-AMC projects  
✅ Automatic project code generation  
✅ Financial tracking (actual vs estimated costs)  
✅ Profit margin monitoring  
✅ Invoice payment tracking  
✅ Visual color-coded indicators for cost overruns and profit thresholds  
✅ Branch management  

## Installation Steps

### 1. Copy Module
Copy the `eq_fc_management` folder to your Odoo addons directory:
```
/path/to/odoo/addons/eq_fc_management/
```

### 2. Update Module List
1. Log into Odoo as Administrator
2. Go to **Apps** menu
3. Click **Update Apps List**
4. Confirm the update

### 3. Install Module
1. Search for **"Equdai Project Financial Control"** or **"eq_fc_management"**
2. Click **Install**

## Initial Configuration

### 1. Configure Project Numbering
1. Navigate to **Financial Control > Project Configuration**
2. Open the default configuration
3. Configure **AMC Projects** tab:
   - Prefix: AMC (or your preference)
   - Suffix: (optional)
   - Padding Digits: 5 (default)
   - Next Number: 1 (starting sequence)
4. Configure **Non-AMC Projects** tab:
   - Prefix: PROJ (or your preference)
   - Suffix: (optional)
   - Padding Digits: 5 (default)
   - Next Number: 1 (starting sequence)
5. Configure **Thresholds** tab:
   - Profit Warning Threshold: 10%
   - Profit Danger Threshold: 5%
   - Cost Warning Threshold: 10%
   - Cost Danger Threshold: 20%

### 2. Create Branches (Optional)
1. Navigate to **Financial Control > Branches**
2. Create branches for organizing projects

## Using the Module

### Creating Projects with Automatic Code Generation
1. Create a new project in **Project** module
2. Fill in project details
3. Check **Is AMC Project** if applicable (or leave unchecked for non-AMC)
4. Select **Branch** if configured
5. Save - The project code will be automatically generated

**Example codes:**
- AMC projects: AMC00001, AMC00002, etc.
- Non-AMC projects: PROJ00001, PROJ00002, etc.

### Tracking Project Financials
1. Open any project
2. Go to **Financial Tracking** tab
3. Enter financial information:

**Costs Section:**
- Estimated Cost: Your budgeted amount
- Actual Cost: Current actual expenditure
- Status indicator will show:
  - 🟢 Green: Within acceptable range
  - 🟠 Orange: Warning threshold exceeded
  - 🔴 Red: Danger threshold exceeded

**Profit Section:**
- Estimated Profit: Your expected profit
- Actual Profit: Calculated automatically (Invoice Total - Actual Cost)
- Status indicator shows profit health

**Invoice Details:**
- Invoice Total: Total invoice amount
- Invoice Paid: Amount received
- Pending: Automatically calculated
- Paid %: Payment progress

### Visual Indicators
- **Green Labels**: Performance within acceptable thresholds
- **Yellow/Orange Labels**: Warning level - attention needed
- **Red Labels**: Critical level - immediate action required

## Configuration Examples

### Example 1: Basic Setup
```
AMC Prefix: AMC
AMC Padding: 5 digits
AMC Next: 1
Result: AMC00001, AMC00002, ...

Non-AMC Prefix: PROJ
Non-AMC Padding: 5 digits
Non-AMC Next: 1
Result: PROJ00001, PROJ00002, ...
```

### Example 2: Custom Format
```
AMC Prefix: AMC-
AMC Suffix: -2024
AMC Padding: 4 digits
AMC Next: 1
Result: AMC-0001-2024, AMC-0002-2024, ...
```

## Troubleshooting

### Issue: Project code not generating
**Solution:** 
- Ensure project configuration exists and is active
- Check if Is AMC Project checkbox is set
- Try creating a new project

### Issue: Colors not showing
**Solution:**
- Update the module (Settings > Apps > Upgrade)
- Clear browser cache
- Check that thresholds are configured

### Issue: Permission denied
**Solution:**
- User must have Project Manager or Project User role
- Check security access rights

## Module Structure
```
eq_fc_management/
├── __init__.py
├── __manifest__.py
├── README.md
├── data/
│   └── fc_project_config_data.xml
├── models/
│   ├── __init__.py
│   ├── fc_project_config.py
│   └── fc_project.py
├── security/
│   └── ir.model.access.csv
├── static/
│   ├── description/
│   │   ├── index.html
│   │   └── icon.png
│   └── src/
│       └── css/
│           └── fc_project_custom.css
└── views/
    ├── fc_project_config_views.xml
    ├── fc_project_views.xml
    └── fc_project_menus.xml
```

## Support
For issues or questions, refer to the README.md file or contact Equdai support.

## License
LGPL-3









