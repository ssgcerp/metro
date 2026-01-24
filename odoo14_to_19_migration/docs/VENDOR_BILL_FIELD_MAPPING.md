# Vendor Bill Field Mapping: Odoo 14 to Odoo 19

This document provides a comprehensive mapping of all fields for Vendor Bills (Purchase Invoices) when migrating from Odoo 14 to Odoo 19.

## Model Changes

- **Odoo 14**: `account.move` (with `move_type='in_invoice'`)
- **Odoo 19**: `account.move` (with `move_type='in_invoice'`)

The model name remains the same, but field names and structures have changed.

---

## Standard Fields Mapping

| Odoo 14 Field | Odoo 19 Field | Type | Notes |
|--------------|---------------|------|-------|
| `id` | `id` | Integer | Record ID (preserved) |
| `name` | `name` | Char | Bill number (preserved) |
| `partner_id` | `partner_id` | Many2one | Vendor/Supplier (required) |
| `invoice_date` | `invoice_date` | Date | Bill date |
| `invoice_date_due` | `invoice_date_due` | Date | Due date |
| `state` | `state` | Selection | Status: draft, posted, cancel |
| `payment_state` | `payment_state` | Selection | Payment status (computed) |
| `amount_total` | `amount_total` | Monetary | Total amount |
| `amount_untaxed` | `amount_untaxed` | Monetary | Untaxed amount |
| `amount_tax` | `amount_tax` | Monetary | Tax amount |
| `currency_id` | `currency_id` | Many2one | Currency (migrated as AED) |
| `journal_id` | `journal_id` | Many2one | Purchase journal |
| `ref` | `ref` | Char | Reference |
| `narration` | `narration` | Text | Notes/Narration |
| `invoice_origin` | `invoice_origin` | Char | Origin (e.g., PO number) |
| `invoice_payment_term_id` | `invoice_payment_term_id` | Many2one | Payment terms |
| `fiscal_position_id` | `fiscal_position_id` | Many2one | Fiscal position |
| `purchase_id` | `purchase_id` | Many2one | Linked Purchase Order |
| `user_id` | `user_id` | Many2one | Responsible user (✅ Migrated) |
| `invoice_line_ids` | `invoice_line_ids` | One2many | Bill lines |
| `line_ids` | `line_ids` | One2many | All account move lines |
| `company_id` | `company_id` | Many2one | Company |
| `branch_id` | `company_id` | Many2one | **Branch (Odoo 14) → Company (Odoo 19)** - Mapped via `odoo14.branch.company.mapping` model. Priority: Excel company > branch_id mapping > company_id > default company |
| `create_date` | `create_date` | Datetime | Creation date (preserved) |
| `write_date` | `write_date` | Datetime | Last write date (preserved) |
| `create_uid` | `create_uid` | Many2one | Created by (preserved) |
| `write_uid` | `write_uid` | Many2one | Last written by (preserved) |

---

## Custom Fields Mapping

### Vendor Bill Header Fields (from metro_erp → eq_fc_purchase_custom & eq_fc_invoice_custom)

| Odoo 14 Field | Odoo 19 Field | Type | Module | Notes |
|--------------|---------------|------|--------|-------|
| `location` | `location` | Char | metro_erp → eq_fc_invoice_custom | ✅ Migrated (via eq_fc_invoice_custom) |
| `site_name` | `site_name` | Char | metro_erp → eq_fc_invoice_custom | ✅ Migrated (via eq_fc_invoice_custom) |
| `create_do` | `create_do` | Boolean | metro_erp → eq_fc_invoice_custom | ✅ Migrated (via eq_fc_invoice_custom) |
| `picking_ids` | ❌ Not migrated | Many2many | metro_erp | Not available in Odoo 19 vendor bills |
| `is_wo_header` | `is_wo_header` | Boolean | metro_erp → eq_fc_purchase_custom | ✅ Migrated |
| `bank_details` | `bank_details` | Text | metro_erp → eq_fc_invoice_custom | ✅ Migrated (via eq_fc_invoice_custom) |
| `file_to_upload` | `file_to_upload` | Binary | metro_erp → eq_fc_invoice_custom | ✅ Migrated (via eq_fc_invoice_custom) |
| `filename` | `filename` | Char | metro_erp → eq_fc_invoice_custom | ✅ Migrated (via eq_fc_invoice_custom) |
| `is_with_stamp` | `is_with_stamp` | Boolean | metro_erp → eq_fc_purchase_custom | ✅ Migrated |
| `voucher_no` | `voucher_number` | Char | metro_erp → eq_fc_purchase_custom | ✅ Migrated (renamed) |
| `in_note` | `in_note` | Text | metro_erp → eq_fc_invoice_custom | ✅ Migrated (via eq_fc_invoice_custom) |
| `lpo_n` | `lpo_number` | Char | metro_erp → eq_fc_purchase_custom | ✅ Migrated (renamed) |
| `quote_reference` | `quote_reference` | Char | metro_erp → eq_fc_purchase_custom | ✅ Migrated (Many2one → Char) |
| `po_no` | `po_number` | Char | metro_erp → eq_fc_purchase_custom | ✅ Migrated (renamed) |

### Vendor Bill Line Fields

| Odoo 14 Field | Odoo 19 Field | Type | Module | Notes |
|--------------|---------------|------|--------|-------|
| `brand_id` | `brand_id` | Many2one | metro_erp | ✅ Migrated (if product.brand exists) |
| `product_id` | `product_id` | Many2one | Standard | ✅ Migrated |
| `name` | `name` | Char | Standard | ✅ Migrated |
| `quantity` | `quantity` | Float | Standard | ✅ Migrated |
| `price_unit` | `price_unit` | Monetary | Standard | ✅ Migrated |
| `discount` | `discount` | Float | Standard | ✅ Migrated |
| `tax_ids` | `tax_ids` | Many2many | Standard | ✅ Migrated |
| `account_id` | `account_id` | Many2one | Standard | ✅ Migrated (expense account) |
| `sequence` | `sequence` | Integer | Standard | ✅ Migrated |
| `purchase_line_id` | `purchase_line_id` | Many2one | Standard | ✅ Migrated (if linked to PO) |

---

## Field Mapping Details

### 1. Currency Migration
- **Always uses AED**: All vendor bills are migrated with AED currency, regardless of original currency
- Original currency is logged but not preserved
- Fallback to company currency if AED not found

### 2. Quote Reference Field
- **Odoo 14**: `quote_reference` (Many2one → `quotation.order`)
- **Odoo 19**: `quote_reference` (Char)
- **Migration**: Extracts the name from the Many2one field and stores as Char

### 3. Voucher Number Field
- **Odoo 14**: `voucher_no`
- **Odoo 19**: `voucher_number`
- **Migration**: Direct mapping with field name change

### 4. LPO Number Field
- **Odoo 14**: `lpo_n`
- **Odoo 19**: `lpo_number`
- **Migration**: Direct mapping with field name change

### 5. PO Number Field
- **Odoo 14**: `po_no`
- **Odoo 19**: `po_number`
- **Migration**: Direct mapping with field name change

### 6. Purchase Order Linking
- **Odoo 14**: `purchase_id` (Many2one)
- **Odoo 19**: `purchase_id` (Many2one)
- **Migration**: 
  - First tries to match by `purchase_id` from Odoo 14
  - Falls back to matching by `invoice_origin` (PO number)
  - Creates link if purchase order exists in Odoo 19

### 7. State/Posting
- **Odoo 14**: `state` field (draft, posted, cancel)
- **Odoo 19**: `state` field (draft, posted, cancel)
- **Migration**:
  - Bills are always created in `draft` state first
  - If original bill was `posted`, it will be posted after creation
  - Excel status can also trigger posting if it contains "posted" or "post"

### 8. Account Mapping for Lines
- **Default**: Uses expense account from product (`property_account_expense_id`)
- **Fallback**: Searches for default expense account for the company
- **Required**: Account is required for each line

---

## Fields NOT Migrated

The following fields from Odoo 14 are **NOT** available in Odoo 19 vendor bills and will be skipped:

1. `picking_ids` - Related stock pickings (Many2many field not available)

**Note**: Most fields from `metro_erp` are now migrated:
- Fields from `eq_fc_purchase_custom`: `quote_reference`, `lpo_number`, `voucher_number`, `po_number`, `is_wo_header`, `is_with_stamp`
- Fields from `eq_fc_invoice_custom`: `location`, `site_name`, `create_do`, `bank_details`, `file_to_upload`, `filename`, `in_note`

Since `eq_fc_invoice_custom` extends `account.move` without domain restrictions, its fields are available on ALL account moves including vendor bills.

---

## Excel Upload Format

When uploading vendor bills via Excel, the following columns are expected:

| Column Name | Field | Type | Required |
|------------|-------|------|----------|
| Number | `uploaded_bill_number` | Text | ✅ Yes |
| Voucher Number | `voucher_number` | Text | No |
| Bill Partner Name | `bill_partner_name` | Text | No |
| Invoice/Bill Date | `invoice_bill_date` | Date | No |
| Due Date | `due_date` | Date | No |
| Status | `excel_status` | Text | No |
| Payment Status | `payment_status` | Text | No |
| Company | `company` | Text | No |
| LPO Number | `lpo_number` | Text | No |
| PO Number | `po_number` | Text | No |
| Quote Reference | `quote_reference` | Text | No |

---

## Migration Process

1. **Upload Excel**: Upload vendor bill numbers via Excel file
2. **Check Status**: Verify bills exist in Odoo 14 and Odoo 19
3. **Queue Migration**: Mark bills as "queued" for migration
4. **Start Migration**: Begin sequential migration process
5. **Migration Steps**:
   - Fetch bill data from Odoo 14
   - Map all standard and custom fields
   - Create vendor bill in Odoo 19 (draft state)
   - Migrate all bill lines
   - Post bill if original was posted
   - Update migration status

---

## Custom Modules Required

### Odoo 19 Modules:
- `eq_fc_purchase_custom` - Provides custom fields for vendor bills:
  - `quote_reference` (Char)
  - `lpo_number` (Char)
  - `voucher_number` (Char)
  - `po_number` (Char)
  - `is_wo_header` (Boolean)
  - `is_with_stamp` (Boolean)

- `eq_fc_invoice_custom` - Provides custom fields for all account moves (including vendor bills):
  - `location` (Char)
  - `site_name` (Char)
  - `create_do` (Boolean)
  - `bank_details` (Text)
  - `file_to_upload` (Binary)
  - `filename` (Char)
  - `in_note` (Text)
  - `amc_contract_id` (Many2one - for customer invoices only)

**Note**: `eq_fc_invoice_custom` extends `account.move` without domain restrictions, so its fields are available on vendor bills too.

### Odoo 14 Modules:
- `metro_erp` - Provides custom fields:
  - All fields listed in "Custom Fields Mapping" section

---

## Notes

1. **Currency**: All bills are migrated with AED currency
2. **State**: Bills are created in draft, then posted if original was posted
3. **Purchase Orders**: Automatically linked if they exist in Odoo 19
4. **Products**: Created if not found, matched by default_code, name, or barcode
5. **Partners**: Created if not found, matched by ID or name
6. **Accounts**: Uses product expense account or default expense account
7. **Dates**: Original creation and write dates are preserved
8. **Users**: Original creator and writer are preserved (matched by login/name/email)

---

## Error Handling

- Failed migrations are logged to `logs/failed_vendor_bill_migrations.log`
- Errors are displayed in the migration line status message
- Migration continues sequentially even if one bill fails
- Bills already existing in Odoo 19 are marked as "already_migrated"

---

## Support

For issues or questions regarding vendor bill migration, please contact the development team.

