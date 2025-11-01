# FM AMC CRM Custom & FM AMC Estimation Modules - Complete Analysis

## Overview

This document provides a comprehensive analysis of the **FM AMC CRM Custom** (`fm_amc_crm_custom`) and **FM AMC Estimation** (`fm_amc_estimation`) modules in your Odoo 19 installation.

---

## Module 1: FM AMC Estimation (`fm_amc_estimation`)

### Purpose
Extends CRM to provide a separate estimation workflow for projects and AMC contracts, with the ability to convert approved estimations into standard CRM quotations.

### Version
19.0.1.0.56

### Dependencies
- `base`, `sales_team`, `sale`, `crm`, `project`, `amc_contracts`, `product`, `stock`

### Core Models

#### 1. `fm.amc.estimation` (Main Estimation Model)
**Key Fields:**
- **Basic Info:**
  - `name`: Auto-generated estimation number (generated on approval)
  - `stage_id`: Current workflow stage
  - `partner_id`: Customer (required)
  - `contact_id`: Contact person
  - `branch_id`: Company/Branch (required, defaults to current company)
  - `sales_contact_id`: Sales contact person
  - `estimation_date`: Date of estimation (defaults to today)
  - `validity_date`: Validity date (must be after estimation date)

- **Integration Fields:**
  - `amc_contract_id`: Link to AMC Contract (filtered by customer)
  - `project_id`: Link to Project (filtered by customer)
  - `sale_order_id`: Created quotation from this estimation (readonly)

- **Financial Fields:**
  - `product_cost`, `installation_price`, `expense`: Individual cost components
  - `total_cost`, `profit`, `price`: Calculated financial values
  - `project_amount_total`: Sum of project estimation lines (untaxed)
  - `consumable_amount_total`: Sum of consumable estimation lines (untaxed)
  - `expense_amount_total`: Sum of expense lines (untaxed)
  - `amount_untaxed`, `amount_tax`, `amount_total`: Total amounts (computed)

- **Lines:**
  - `line_ids`: All estimation lines (One2many)
  - `project_line_ids`: Project estimation lines only (same inverse, different domain)
  - `consumable_line_ids`: Consumable estimation lines only (same inverse, different domain)
  - `expense_line_ids`: Expense lines only (same inverse, different domain)

- **Computed Flags:**
  - `is_draft`: True if stage is "Draft"
  - `is_waiting_approval`: True if stage is "Waiting Approval"
  - `is_approved`: True if stage is "Approved"
  - `is_locked`: True if stage is locked

**Key Methods:**
- `action_submit_for_approval()`: Moves to "Waiting Approval" stage (validates lines exist)
- `action_approve()`: Approves estimation, generates estimation number
- `action_lock()`: Locks estimation (prevents modifications)
- `action_reset_to_draft()`: Resets to draft stage
- `action_create_quotation()`: Creates `sale.order` from approved estimation
- `_generate_estimation_number()`: Generates estimation number based on config (supports AMC format)

**Business Rules:**
- Estimation number is generated only when moved to "Approved" stage
- Number format differs if AMC contract is linked (uses AMC format)
- Locked estimations cannot be modified (except by system admin)
- Must have at least one line before submission for approval
- Only approved estimations can create quotations

#### 2. `fm.amc.estimation.line` (Estimation Line Items)
**Key Fields:**
- `estimation_id`: Parent estimation (required)
- `sequence`: Line ordering
- `line_type`: Selection field - `'project'`, `'consumable'`, `'expense'`
- `product_id`: Product (optional)
- `product_template_id`: Related product template
- `name`: Description (required)
- `product_uom_qty`: Quantity (default 1.0)
- `product_uom`: Unit of Measure
- `price_unit`: Unit price (required)
- `tax_id`: Taxes (Many2many)
- `price_subtotal`, `price_tax`, `price_total`: Computed amounts
- `currency_id`: Related from estimation

**Features:**
- Automatic tax calculation
- Product onchange fills name, UOM, price, and taxes

#### 3. `fm.amc.estimation.stage` (Workflow Stages)
**Default Stages:**
1. **Draft** (sequence 10, color 1)
   - Initial state, can be modified
   - `is_default=True`, `is_approved_stage=False`, `is_locked_stage=False`

2. **Waiting Approval** (sequence 20, color 3)
   - Submitted for approval
   - `is_default=True`, `is_approved_stage=False`, `is_locked_stage=False`

3. **Approved** (sequence 30, color 10)
   - Approved state, estimation number generated
   - `is_default=True`, `is_approved_stage=True`, `is_locked_stage=False`
   - Quotation can be created at this stage

4. **Locked** (sequence 40, color 2)
   - Final state, cannot be modified
   - `is_default=True`, `is_approved_stage=False`, `is_locked_stage=True`
   - Folded in kanban

**Protection:**
- Default stages cannot be deleted
- Stages in use cannot be deleted

#### 4. `fm.amc.estimation.config` (Estimation Number Configuration)
**Configuration Fields:**
- `prefix`: Prefix (default: "EST")
- `module_code`: Module code (default: "EST")
- `amc_prefix`: AMC prefix (default: "AMC")
- `use_branch_code`: Include branch code (default: True)
- `use_year`: Include year (default: True)
- `padding_digits`: Sequence padding (default: 4)
- `separator`: Number separator (default: "/")
- `format_text`: Custom format template (standard estimations)
- `amc_estimation_format_text`: Custom format for AMC estimations
- `next_number`: Manual sequence override

**Number Generation:**
- Standard format: `{prefix}/{modulecode}/{branchcode}/{nextnumber}/{year}`
  - Example: `EST/EST/FUJ/1213/2025`
- AMC format: Used when AMC contract is linked
  - Format: `{prefix}/AMC/{modulecode}/{branchcode}/{nextnumber}/{year}`
  - Uses separate sequence: `fm.amc.estimation.sequence.amc`
- Standard sequence: `fm.amc.estimation.sequence`

#### 5. `fm.amc.product.sku.config` (Product SKU Configuration)
**SKU Types:**
- **Estimation SKU**: Used in estimations and quotations
  - Prefix: `EST-SKU` (configurable)
  - Sequence: `fm.amc.estimation.sku.sequence`
- **Default SKU**: Used in sales orders
  - Prefix: `SKU` (configurable)
  - Sequence: `fm.amc.product.sku.sequence`

**Configuration:**
- `estimation_sku_prefix`, `default_sku_prefix`
- `sku_padding_digits` (default: 6)
- `sku_separator` (default: "-")
- `estimation_sku_next_number`, `default_sku_next_number` (manual override)

#### 6. `product.template` (Extended)
**New Fields:**
- `estimation_sku`: SKU for estimations/quotations (auto-generated)
- `default_sku`: SKU for sales orders (auto-generated)

**Auto-generation:**
- SKUs are automatically generated when product is created if not provided

### Views

#### Estimation Form View
- **Header:** Statusbar with stages, workflow buttons (context-aware visibility)
- **Main Section:**
  - Customer info, AMC Contract, Project, Branch, Sales Contact
  - Dates, financial totals
  - Currency, created quotation link
- **Notebook Tabs:**
  1. **Project Estimations**: Project-type lines with subtotal
  2. **Consumable Estimations**: Consumable-type lines with subtotal
  3. **Expense**: Expense-type lines with subtotal
  4. **Terms and Conditions**: HTML notes field
- **Chatter**: Mail thread for communication

#### Estimation List View
- Columns: Estimation Number, Date, Customer, AMC Contract, Project, Total Amount, Stage (badge)

#### Estimation Kanban View
- Grouped by stage
- Shows estimation details, customer, amounts

#### Estimation Search View
- Filters: Draft, Waiting Approval, Approved, Locked, With/Without Quotation
- Group by: Stage, Customer, AMC Contract, Project

### Security
- **Sales Manager**: Full access (read, write, create, delete)
- **Sales User**: Can create/modify own estimations, cannot delete

### Menu Structure
- **Sales > Estimations**: Main estimations menu
- **AMC Settings > Estimations Format**: Configuration
- **AMC Settings > Estimations Stages**: Stage management
- **Inventory > Configuration > Product SKU Configuration**: SKU settings

### Assets (Frontend)
- CSS: `fm_amc_estimation_custom.css`
- JS: `fm_amc_estimation_menu.js`

---

## Module 2: FM AMC CRM Custom (`fm_amc_crm_custom`)

### Purpose
Extends standard Odoo Sale Order (quotations) with custom workflow stages and estimation integration.

### Version
19.0.1.0.80

### Dependencies
- `base`, `crm`, `sale_management`, `fm_amc_estimation`

### Core Models

#### 1. `sale.order` (Extended)
**New Fields:**
- **Estimation Integration:**
  - `estimation_id`: Link to `fm.amc.estimation` (tracking)
  - `estimated_value`: Computed from estimation (untaxed amount)
  - `is_estimation_order`: Boolean flag if linked to estimation

- **Custom Workflow:**
  - `quotation_stage_id`: Custom workflow stage (replaces/extends standard state)
  - `printed_without_approval`: Flag if printed before approval

- **Stage Flags (Computed):**
  - `is_draft_stage`: True if stage code is 'draft'
  - `is_pending_approval_stage`: True if stage code is 'pending_approval'
  - `is_quotation_stage`: True if stage code is 'quotation'
  - `is_quotation_sent_stage`: True if stage code is 'quotation_sent'
  - `is_sales_order_stage`: True if stage code is 'sales_order'
  - `is_locked`: True if stage is locked

**Key Methods:**
- `action_send_for_approval()`: Move to "Pending Approval" stage
- `action_approve()`: Move to "Quotation" stage (after approval)
- `action_reject()`: Move back to "Draft" stage
- `action_mark_quotation_sent()`: Move to "Quotation Sent" stage
- `action_cancel_quotation()`: Move to "Cancelled" stage
- `action_reset_to_draft()`: Reset to "Draft" stage
- `action_mark_printed()`: Mark as printed (flags if printed before approval)

#### 2. `sale.order.line` (Extended)
**New Fields:**
- `estimated_price`: Computed from linked estimation line (unit price)

**Computation:**
- Searches estimation lines by product_id
- Returns unit price from matching estimation line, or 0.0

#### 3. `sale.quotation.stage` (Custom Workflow Stages)
**Default Stages:**
1. **Draft** (sequence 10, color 0)
   - `code='draft'`, `is_draft_stage=True`, `is_locked_stage=False`

2. **Pending Approval** (sequence 20, color 5)
   - `code='pending_approval'`, `is_draft_stage=False`

3. **Quotation** (sequence 30, color 10)
   - `code='quotation'`, `is_draft_stage=False`

4. **Quotation Sent** (sequence 40, color 3)
   - `code='quotation_sent'`, `is_draft_stage=False`

5. **Sales Order** (sequence 50, color 4)
   - `code='sales_order'`, `is_locked_stage=True`

6. **Cancelled** (sequence 60, color 1)
   - `code='cancelled'`, `is_cancelled_stage=True`, `is_locked_stage=True`

**Fields:**
- `name`: Stage name (translatable)
- `sequence`: Ordering
- `code`: Programmatic reference (required, unique)
- `fold`: Fold in kanban
- `is_draft_stage`, `is_locked_stage`, `is_cancelled_stage`: Behavior flags
- `color`: Color code for UI

#### 4. `sale.quotation.config` (Configuration)
**Configuration Fields:**
- Stage color configuration:
  - `draft_stage_color` (default: 0)
  - `pending_approval_stage_color` (default: 5)
  - `quotation_stage_color` (default: 10)
  - `quotation_sent_stage_color` (default: 3)
  - `sales_order_stage_color` (default: 4)
  - `cancelled_stage_color` (default: 1)

### Views

#### Sale Order Form View (Extended)
- **Header:** Custom workflow buttons (context-aware based on stage):
  - Draft: "Send for Approval", "Print"
  - Pending Approval: "Approve for Quotation", "Decline", "Print"
  - Quotation: "Mark as Sent", "Cancel"
  - Quotation Sent: "Confirm", "Cancel"
  - Sales Order: "Reset to Draft", "Cancel"
- **Statusbar:** Shows `quotation_stage_id` after `state` field
- **Estimation Fields:** 
  - `estimation_id`: Many2one field (domain: approved estimations for customer)
  - `estimated_value`: Readonly computed field
  - `is_estimation_order`: Invisible computed field

#### Sale Order List View (Extended)
- Added `estimated_value` column (optional, hideable)

#### Sale Order Line View (Custom)
- Shows `estimated_price` column
- Editable inline list
- Handles sections and notes

### Workflow Integration
The custom quotation stages work alongside the standard Odoo `state` field:
- Standard states still exist (draft, sent, sale, etc.)
- Custom `quotation_stage_id` provides additional workflow control
- Buttons are shown/hidden based on custom stage flags

### Security
- **Sales Manager**: Full access to stages and config (read, write, create, delete)
- **Sales User**: Read-only access to stages and config

### Menu Structure
- **Sales > My Quotations**: Direct access to quotations (filtered by user)

---

## Integration Between Modules

### Estimation to Quotation Flow
1. **Create Estimation** → Fill details, add lines (project/consumable/expense)
2. **Submit for Approval** → Moves to "Waiting Approval" stage
3. **Approve** → Moves to "Approved" stage, generates estimation number
4. **Create Quotation** → Creates `sale.order` with:
   - Same customer, contact, project
   - Origin set to estimation number
   - All estimation lines copied to sale order lines
   - `estimation_id` link established
5. **Quotation Workflow** → Can proceed through custom stages (Draft → Pending Approval → Quotation → Quotation Sent → Sales Order)

### Data Flow
- Estimation lines → Sale Order lines (on quotation creation)
- Estimation amounts → Quotation estimated value (computed)
- Estimation line prices → Sale Order line estimated prices (computed)

### Product SKU Usage
- Products have two SKUs:
  - **Estimation SKU**: Shown in estimations and quotations
  - **Default SKU**: Shown in sales orders

---

## Key Features Summary

### FM AMC Estimation Module
✅ Separate estimation workflow for projects/AMC contracts  
✅ Multi-stage approval process (Draft → Waiting Approval → Approved → Locked)  
✅ Automatic estimation number generation (with AMC format support)  
✅ Three line types: Project, Consumable, Expense  
✅ Integration with AMC Contracts and Projects  
✅ Convert to standard quotations  
✅ Customizable number format (prefix, branch code, year, sequence)  
✅ Product SKU management (estimation SKU vs default SKU)  
✅ Lock mechanism to prevent modifications  

### FM AMC CRM Custom Module
✅ Custom quotation workflow stages  
✅ Integration with estimation module (link estimations to quotations)  
✅ Estimated value tracking on quotations  
✅ Estimated price on quotation lines  
✅ Print tracking (flags if printed before approval)  
✅ Stage-based button visibility  
✅ Statusbar visualization of workflow  

---

## Configuration Points

### Estimation Module
1. **Estimation Number Format** (`fm.amc.estimation.config`)
   - Configure prefix, module code, branch code, year, padding
   - Custom format templates (standard and AMC)

2. **Estimation Stages** (`fm.amc.estimation.stage`)
   - Default stages are protected
   - Can add custom stages

3. **Product SKU** (`fm.amc.product.sku.config`)
   - Configure SKU prefixes and sequences

### CRM Custom Module
1. **Quotation Stages** (`sale.quotation.stage`)
   - Default stages defined in data file
   - Can be modified by managers

2. **Quotation Configuration** (`sale.quotation.config`)
   - Configure stage colors

---

## Technical Notes

### Sequences Used
- `fm.amc.estimation.sequence`: Standard estimation numbers
- `fm.amc.estimation.sequence.amc`: AMC estimation numbers
- `fm.amc.estimation.sku.sequence`: Estimation SKUs
- `fm.amc.product.sku.sequence`: Default product SKUs

### Computed Fields
- Most financial fields use `store=True` for performance
- Stage flags are computed on-the-fly (no store) for flexibility

### Security Groups
- Both modules use standard Odoo sales groups:
  - `sales_team.group_sale_manager`: Full access
  - `sales_team.group_sale_salesman`: Limited access

### Data Files
- Stage data files use `noupdate="1"` for estimation stages (protected)
- Stage data files use `noupdate="0"` for quotation stages (can be updated)

---

## Potential Areas for Enhancement

1. **Reporting**: Add reports for estimations, conversion rates
2. **Email Integration**: Send estimation/quotation emails with custom templates
3. **Approval Workflow**: Multi-level approval (currently single approval)
4. **Pricing Rules**: Automatic pricing from estimation to quotation
5. **Validation**: More validation rules (e.g., minimum amounts, required fields)
6. **Notifications**: Automatic notifications on stage changes
7. **Analytics**: Dashboard for estimation/quotation metrics

---

## Files Summary

### FM AMC Estimation Module
- **Models**: 6 Python files
- **Views**: 7 XML files
- **Data**: 3 XML files
- **Security**: 1 CSV file
- **Static**: CSS and JS files
- **README**: Documentation

### FM AMC CRM Custom Module
- **Models**: 4 Python files
- **Views**: 4 XML files
- **Data**: 2 XML files
- **Security**: 1 CSV file

---

This analysis provides a complete overview of both modules. Both are well-structured, follow Odoo best practices, and provide a solid foundation for estimation-to-quotation workflows.

