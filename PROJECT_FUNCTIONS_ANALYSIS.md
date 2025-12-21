# Project Functions Analysis - Reference Guide

## Module: `eq_fc_management` (Equdai Project Financial Control)

This module extends `project.project` with comprehensive project management functionality.

### Key Models

#### 1. **Project Model Extensions** (`fc_project.py`)

**Model:** `project.project` (inherited)

**Key Fields:**
- `project_code` - Auto-generated project code (readonly, default='DRAFT')
- `amc_contract_id` - Many2one to `amc.contract` (linked AMC contract)
- `partner_id` - Many2one to `res.partner` (Customer, required)
- `company_id` - Many2one to `res.company` (Company, required)
- `stage_id` - Many2one to `fc.project.stage` (Project stage)
- `branch_id` - Many2one to `res.branch` (Branch associated with project)

**Financial Fields:**
- `estimated_cost` - Monetary (Estimated project cost)
- `actual_cost` - Monetary (Actual project cost)
- `cost_overrun` - Monetary (computed: actual_cost - estimated_cost)
- `cost_overrun_percent` - Float (computed percentage)
- `cost_label_color` - Char (computed: 'danger', 'warning', 'success')
- `estimated_profit` - Monetary (Estimated project profit)
- `actual_profit` - Monetary (computed: invoice_total - actual_cost)
- `profit_percent` - Float (computed percentage)
- `profit_label_color` - Char (computed: 'danger', 'warning', 'success')
- `invoice_total` - Monetary (Total invoice amount)
- `invoice_paid` - Monetary (Total invoice amount paid)
- `invoice_pending` - Monetary (computed: invoice_total - invoice_paid)
- `invoice_paid_percent` - Float (computed percentage)
- `currency_id` - Many2one to `res.currency` (required)
- `is_confirmed` - Boolean (Confirmed status)

**Stage Action Flags (computed):**
- `stage_allow_confirm` - Boolean
- `stage_allow_cancel` - Boolean
- `stage_is_confirmed_stage` - Boolean
- `stage_is_completed_stage` - Boolean

### Key Methods Available

#### **Stage Management Methods:**

1. **`action_next_stage()`**
   - Moves project to the next configured stage (excluding confirmed stage)
   - Usage: `project.action_next_stage()`
   - Returns: `True`

2. **`action_confirm_project()`**
   - Moves project from draft to confirmed stage and generates project code
   - Automatically generates project code using `fc.project.config.generate_project_code()`
   - Sets `is_confirmed = True`
   - Usage: `project.action_confirm_project()`
   - Returns: `True`

3. **`action_cancel_project()`**
   - Moves project to the configured cancelled stage
   - Sets `is_confirmed = False`
   - Usage: `project.action_cancel_project()`
   - Returns: `True`

4. **`action_start_project()`**
   - Advances an awarded/confirmed project into the next stage (typically In Progress)
   - Only works if project is in confirmed stage
   - Usage: `project.action_start_project()`
   - Returns: `True`

5. **`action_complete_project()`**
   - Moves project into the configured completed stage
   - Usage: `project.action_complete_project()`
   - Returns: `True`

#### **Stage Finding Methods:**

6. **`_find_next_stage(current_stage=None)`**
   - Finds the next stage after the current stage
   - Returns: `fc.project.stage` recordset
   - Usage: `next_stage = project._find_next_stage()`

7. **`_find_completed_stage(company_id=None)`**
   - Finds the completed stage for the company
   - Returns: `fc.project.stage` recordset
   - Usage: `completed_stage = project._find_completed_stage()`

8. **`_find_confirmed_stage(company_id=None)`**
   - Finds the confirmed/awarded stage for the company
   - Returns: `fc.project.stage` recordset
   - Usage: `confirmed_stage = project._find_confirmed_stage()`

#### **Helper Methods:**

9. **`_is_amc_project()`**
   - Checks if project is linked to an AMC contract
   - Returns: `Boolean`
   - Usage: `is_amc = project._is_amc_project()`

10. **`_onchange_amc_contract()`**
    - Onchange method for `partner_id` and `company_id`
    - Filters AMC contracts based on customer and company
    - Usage: Automatic when customer/company changes

11. **`action_view_dashboard()`**
    - Opens project dashboard view
    - Returns: Action dictionary
    - Usage: `action = project.action_view_dashboard()`

#### **Computed Methods:**

12. **`_compute_cost_metrics()`**
    - Computes: `cost_overrun`, `cost_overrun_percent`, `cost_label_color`
    - Depends on: `actual_cost`, `estimated_cost`
    - Color logic based on `fc.project.config` thresholds

13. **`_compute_profit_metrics()`**
    - Computes: `actual_profit`, `profit_percent`, `profit_label_color`
    - Depends on: `invoice_total`, `actual_cost`
    - Color logic based on `fc.project.config` thresholds

14. **`_compute_invoice_metrics()`**
    - Computes: `invoice_pending`, `invoice_paid_percent`
    - Depends on: `invoice_total`, `invoice_paid`

15. **`_compute_stage_action_flags()`**
    - Computes stage action visibility flags
    - Depends on: `stage_id`, `company_id`

#### **Model Methods:**

16. **`create(vals_list)`**
    - Overridden to set default stage if not provided
    - Automatically assigns default draft stage

17. **`write(vals)`**
    - Overridden to generate project code when stage changes to confirmed
    - Prevents manual stage changes to confirmed stage (must use Confirm button)
    - Prevents moving confirmed projects backward

18. **`_read_group_stage_ids(stages, domain, order)`**
    - Ensures status bar displays all active stages for the company
    - Used for kanban view grouping

19. **`_set_default_stage_for_existing_projects()`**
    - Sets default stage for existing projects without a stage
    - Usage: `self.env['project.project']._set_default_stage_for_existing_projects()`

#### **Constraints:**

20. **`_check_invoice_paid()`**
    - Constraint: Ensures `invoice_paid` doesn't exceed `invoice_total`
    - Raises: `UserError` if violated

---

#### 2. **Project Configuration Model** (`fc_project_config.py`)

**Model:** `fc.project.config`

**Key Methods:**

1. **`generate_project_code(project=None, is_amc=False)`**
   - Generates project code based on configuration
   - Parameters:
     - `project`: `project.project` record (optional)
     - `is_amc`: Boolean (True for AMC projects, False for regular projects)
   - Returns: String (project code)
   - Usage: 
     ```python
     config = self.env['fc.project.config'].get_config()
     code = config.generate_project_code(project=project, is_amc=True)
     ```
   - Format placeholders: `{prefix}`, `{modulecode}`, `{branchcode}`, `{nextnumber}`, `{year}`, `{suffix}`

2. **`get_config()`**
   - Gets the active configuration (creates default if none exists)
   - Returns: `fc.project.config` recordset
   - Usage: `config = self.env['fc.project.config'].get_config()`

**Key Fields:**
- `amc_prefix`, `amc_suffix`, `amc_padding` - AMC project numbering
- `non_amc_prefix`, `non_amc_suffix`, `non_amc_padding` - Non-AMC project numbering
- `amc_format_text`, `non_amc_format_text` - Custom format templates
- `next_number` - Common sequence number
- `include_branch_code`, `include_year` - Format options
- `profit_warning_threshold`, `profit_danger_threshold` - Profit thresholds (%)
- `cost_warning_threshold`, `cost_danger_threshold` - Cost overrun thresholds (%)

---

#### 3. **Project Stage Model** (`fc_project_stage.py`)

**Model:** `fc.project.stage`

**Key Fields:**
- `name` - Stage name (required)
- `sequence` - Order of stages
- `is_confirmed_stage` - Boolean (Project code generated at this stage)
- `is_draft_stage` - Boolean (Mark as draft stage)
- `is_completed_stage` - Boolean (Mark as completed stage)
- `is_cancel_stage` - Boolean (Cancellation stage)
- `allow_confirm_action` - Boolean (Show Confirm button)
- `allow_next_action` - Boolean (Show Next button)
- `allow_cancel_action` - Boolean (Show Cancel button)
- `company_id` - Many2one to `res.company` (Company-specific stages)
- `active` - Boolean (Active status)

---

### Integration with AMC Quotations

**How to use project functions in `amc.quotation`:**

```python
# Example: Link quotation to project and use project functions
project = self.env['project.project'].browse(project_id)

# Check if project is AMC project
is_amc = project._is_amc_project()

# Get project code
project_code = project.project_code

# Get financial metrics
estimated_cost = project.estimated_cost
actual_cost = project.actual_cost
actual_profit = project.actual_profit

# Get stage information
stage = project.stage_id
is_confirmed = project.is_confirmed

# Move project to next stage
if project.stage_allow_confirm:
    project.action_confirm_project()

# Get project configuration
config = self.env['fc.project.config'].get_config()
code = config.generate_project_code(project=project, is_amc=is_amc)
```

---

### Module: `eq_project_dashboard`

**Additional Project Dashboard Functions:**

1. **`action_open_project_dashboard()`** (in `project.project`)
   - Opens project dashboard client action
   - Returns: Client action dictionary

2. **`get_project_dashboard_values(project_id)`** (in `project.dashboard.helper`)
   - Computes dashboard KPIs and chart data
   - Returns: Dictionary with dashboard values
   - Usage:
     ```python
     helper = self.env['project.dashboard.helper']
     values = helper.get_project_dashboard_values(project_id)
     ```

3. **`_compute_invoice_totals(project)`** (in `project.dashboard.helper`)
   - Computes invoice totals for project
   - Returns: Tuple (total, paid, pending)

4. **`_compute_actual_cost(project)`** (in `project.dashboard.helper`)
   - Computes actual cost from analytic entries, purchases, expenses
   - Returns: Float (total cost)

---

### Usage Examples for AMC Quotations

```python
# In amc.quotation model:

# 1. Get project and check if it's AMC
project = self.project_id
if project:
    is_amc = project._is_amc_project()
    
    # 2. Get project financial data
    estimated_cost = project.estimated_cost
    actual_cost = project.actual_cost
    profit = project.actual_profit
    
    # 3. Get project stage
    stage = project.stage_id
    is_confirmed = project.is_confirmed
    
    # 4. Generate project code (if needed)
    config = self.env['fc.project.config'].get_config()
    code = config.generate_project_code(project=project, is_amc=is_amc)
    
    # 5. Move project to confirmed stage
    if project.stage_allow_confirm:
        project.action_confirm_project()
```

---

### Dependencies

- `project` - Base Odoo project module
- `amc_contracts` - AMC Contracts module
- `account` - Accounting module
- `sms` - SMS notifications

---

### Notes

- Project code is auto-generated when project reaches confirmed stage
- Stage transitions are controlled (cannot manually move to confirmed stage)
- Financial metrics are computed automatically
- Color coding for cost overrun and profit based on configurable thresholds
- Projects can be linked to AMC contracts via `amc_contract_id` field










