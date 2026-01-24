# FM AMC Estimation Module

## Overview
This module extends the CRM module and integrates with the AMC Contracts module to provide a separate estimation workflow for projects and AMC contracts.

## Features

### 1. Estimation Management
- Separate estimation workflow from standard CRM quotations
- Designed specifically for projects and AMC contracts
- Full lifecycle management with status tracking

### 2. Status Workflow
- **Draft**: Initial state, can be modified
- **Waiting Approval**: Submitted for approval
- **Approved**: Approved and ready for quotation creation (estimation number is generated)
- **Locked**: Final state, cannot be modified

### 3. Integration
- Link estimations to AMC Contracts (`amc.contract`)
- Link estimations to Projects (`project.project`)
- Convert approved estimations to standard CRM quotations (`sale.order`)
- All estimation lines (project and consumable) are carried forward to the quotation

### 4. Estimation Lines
- Support for both project and consumable estimation types
- Full product integration
- Quantity, unit price, taxes, and subtotal calculations
- Comprehensive line item management

### 5. Number Format Configuration
- Customizable estimation number format (similar to AMC Contracts)
- Supports:
  - Prefix (e.g., EST)
  - Module code (e.g., EST)
  - Branch code
  - Sequential number with padding
  - Year
- Default format: `EST/EST/[BRANCH]/[SEQUENCE]/[YEAR]`
- Example: `EST/EST/FUJ/1213/2025`

## Installation

1. Place the module in your Odoo addons path
2. Update the apps list
3. Install "FM AMC Estimation" module

## Dependencies
- `base`
- `sale`
- `crm`
- `project`
- `amc_contracts`

## Usage

### Creating an Estimation

1. Navigate to **Sales > Estimations**
2. Click **Create**
3. Fill in the required fields:
   - Customer (required)
   - AMC Contract (optional, filtered by customer)
   - Project (optional)
   - Estimation Date (defaults to today)
   - Validity Date (optional)

### Adding Estimation Lines

1. In the Estimation form, go to the **Estimation Lines** tab
2. Click **Add a line** or use the inline editing
3. For each line:
   - Select line type (Project Estimation or Consumable Estimation)
   - Select product (optional)
   - Enter description
   - Set quantity and unit price
   - Add taxes if needed

### Workflow

1. **Draft**: Create and edit the estimation
2. **Submit for Approval**: Click "Submit for Approval" button (validation ensures at least one line exists)
3. **Approval**: Manager clicks "Approve" button (estimation number is generated)
4. **Create Quotation**: Once approved, click "Create Quotation" button to convert to a standard CRM quotation
5. **Lock** (optional): Lock the estimation to prevent further modifications

### Configuration

Navigate to **Sales > Configuration > Estimation Configuration** to:
- Set estimation number format
- Configure prefix, module code, separator
- Enable/disable branch code and year
- Set padding digits
- Define custom format template

## Technical Details

### Models

- `fm.amc.estimation`: Main estimation model
- `fm.amc.estimation.line`: Estimation line items
- `fm.amc.estimation.stage`: Estimation stages
- `fm.amc.estimation.config`: Estimation number format configuration

### Access Rights

- **Sales Manager**: Full access (read, write, create, delete)
- **Sales User**: Can create and modify own estimations, cannot delete

### Number Generation

Estimation numbers are automatically generated when an estimation is approved (moves to "Approved" stage). The format is configurable through the Estimation Configuration.

## Support

For issues or questions, please contact support or refer to the documentation.



