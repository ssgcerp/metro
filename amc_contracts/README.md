# AMC Contracts Management Module for Odoo 19

## Overview

Comprehensive Annual Maintenance Contract (AMC) management system for Odoo 19 Enterprise/Community.

## Features

### 1. Contract Lifecycle Management
- **Status Management**: Draft, Confirmed, Cancelled, Blocked, Expired
- **Dynamic Status Reordering**: Reorder statuses while default ones cannot be deleted
- **State Transitions**: Smart buttons for Confirm, Cancel, Block, Reset actions
- **Automatic Contract Numbering**: Generated when contract moves to Confirmed status

### 2. Flexible Contract Number Format
- **Customizable Format**: Configure prefix, module code, branch code, sequential number, and year
- **Format Example**: `MFS/AMC/FUJ/1213/2025`
- **Configurable Separator**: Change the separator between format parts
- **Branch Integration**: Automatic branch code detection from company/branch
- **Year Support**: Automatic year inclusion from contract dates

### 3. Comprehensive Contract Information
- **Customer Management**: Customer and contact person selection
- **Project Site**: Project location tracking
- **Branch Assignment**: Multi-company/branch support
- **Sales Contact**: Employee assignment for sales tracking
- **Financial Tracking**: Contract value, labour expense, extra expense, and total calculation
- **Visit Management**: Number of visits and completion tracking
- **Document Options**: Header and stamp options for printed documents

### 4. Tabbed Information Management
- **Types of Services**: Define service types with visit frequency
- **Registration Details**: Contract registration information
- **Invoice Schedule**: Scheduled invoices with status tracking
- **Quotation Details**: Linked quotations and sale orders
- **Service Schedules**: Planned and completed service visits
- **Call Out**: Emergency call-out tracking
- **Additional Jobs**: Extra work tracking with billing
- **Terms and Condition**: Contract terms management
- **Agreement**: Signed agreements with attachments
- **Expenses**: Expense tracking by type
- **Other Info**: Additional notes and information

## Installation

1. Copy the `amc_contracts` folder to your Odoo addons directory
2. Update the apps list in Odoo
3. Install the "AMC Contracts Management" module

## Configuration

### Contract Number Format Setup

1. Go to **AMC > AMC Settings > Contract Configuration**
2. Configure:
   - **Prefix**: e.g., "MFS"
   - **Module Code**: e.g., "AMC"
   - **Use Branch Code**: Enable/disable branch code inclusion
   - **Use Year**: Enable/disable year inclusion
   - **Separator**: Character to separate format parts (default: "/")
   - **Padding Digits**: Number of digits for sequential number (default: 4)

### Status/Stage Management

1. Go to **AMC > AMC Settings > Contract Stages**
2. Default stages (Draft, Confirmed, Cancelled, Blocked, Expired) cannot be deleted
3. Reorder stages by changing the sequence number
4. Add custom stages as needed
5. Mark one stage as "Confirmed Stage" to trigger contract number generation

## Usage

### Creating a Contract

1. Navigate to **AMC > AMC Contracts**
2. Click **Create**
3. Fill in required fields:
   - Customer
   - Branch
   - Contract Date
   - Start Date
   - End Date
   - Contract Value
4. Add service types in the "Types of Services" tab
5. Add other information as needed
6. Click **Confirm** to activate the contract

### Contract Actions

- **Confirm**: Move contract from Draft to Confirmed (generates contract number)
- **Reset**: Return contract to Draft status
- **Cancel**: Mark contract as Cancelled
- **Block**: Block the contract from further processing
- **Create Sale**: Create a sale order from the contract
- **Create Visits**: Automatically create scheduled visits based on number of visits

### Visit Management

1. Set the **Number of Visits** field
2. Click **Create Visits** button (available when contract is Confirmed)
3. Visits are automatically scheduled based on contract dates
4. Track visit completion in the **Service Schedules** tab

## Models

### Main Models
- `amc.contract`: Main contract model
- `amc.contract.config`: Configuration for contract numbering
- `amc.contract.stage`: Contract status/stage management

### Related Models
- `amc.contract.type.of.service`: Service types
- `amc.contract.registration`: Registration details
- `amc.contract.invoice.schedule`: Invoice scheduling
- `amc.contract.quotation`: Quotation information
- `amc.contract.service.schedule`: Service visit scheduling
- `amc.contract.call.out`: Emergency call-outs
- `amc.contract.additional.job`: Additional work tracking
- `amc.contract.agreement`: Agreement management
- `amc.contract.expense`: Expense tracking

## Technical Details

### Dependencies
- `base`: Core Odoo framework
- `sale`: Sale order integration
- `account`: Accounting and invoicing
- `contacts`: Partner management
- `hr`: Employee management

### Security
- Standard user access for contract management
- System administrator access for configuration
- Access rights defined in `security/ir.model.access.csv`

## Customization

### Contract Number Format

The contract number is generated using the formula:
```
[PREFIX]/[MODULE_CODE]/[BRANCH_CODE]/[SEQUENTIAL]/[YEAR]
```

All parts except sequential number are optional based on configuration.

### Branch Code Detection

The module automatically detects branch codes from:
1. `res.branch` model if available (checks `code` field)
2. Company `code` field if available
3. First 3 characters of company name as fallback

## Support

For issues and questions, please contact your Odoo administrator.

## License

LGPL-3






