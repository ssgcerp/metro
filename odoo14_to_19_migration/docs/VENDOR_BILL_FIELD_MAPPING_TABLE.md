# Vendor Bill (account.move) Field Mapping Table
## Odoo 14 to Odoo 19 Migration

**Document Version:** 1.0  
**Last Updated:** 2025-01-22  
**Purpose:** Comprehensive field mapping between Odoo 14 and Odoo 19 vendor bills (account.move) including custom fields

---

## Executive Summary

This document provides a detailed mapping of all fields for vendor bills (`account.move` with `move_type` in `('in_invoice', 'in_refund')`) between Odoo 14 and Odoo 19, including:
- Standard Odoo fields
- Custom fields from `eq_fc_purchase_custom` (Odoo 19)
- Custom fields from Odoo 14 modules (if any)

**Status Legend:**
- ✅ **Mapped** - Field is fetched from Odoo 14 and mapped to Odoo 19
- ⚠️ **Not Mapped** - Field exists but is not being migrated
- ❌ **Issue** - Field mapping has problems or missing
- 🔍 **Not Found** - Field not found in source/target

---

## 1. Standard Odoo Fields - account.move (Vendor Bill Header)

| # | Odoo 14 Field | Odoo 19 Field | Status | Notes |
|---|---------------|---------------|--------|-------|
| 1 | `id` | N/A | ✅ | Used for identification only |
| 2 | `name` | `ref` | ✅ | Odoo 14 bill name stored in `ref` field |
| 3 | `partner_id` | `partner_id` | ✅ | Vendor/Supplier - mapped via purchase order partner |
| 4 | `invoice_date` | `invoice_date` | ✅ | Invoice date |
| 5 | `invoice_date_due` / `date_due` | `invoice_date_due` | ✅ | Due date (set after creation) |
| 6 | `state` | `state` | ⚠️ | Not directly mapped - set via `action_post()` if state was 'posted' |
| 7 | `amount_total` | `amount_total` | ⚠️ | Computed field - recalculated after lines migration |
| 8 | `amount_untaxed` | `amount_untaxed` | ⚠️ | Computed field - recalculated after lines migration |
| 9 | `amount_tax` | `amount_tax` | ⚠️ | Computed field - recalculated after lines migration |
| 10 | `currency_id` | `currency_id` | ✅ | Currency - mapped from purchase order or Odoo 14 |
| 11 | `journal_id` | `journal_id` | ✅ | Journal - mapped by name/type |
| 12 | `ref` | `ref` | ✅ | Reference - stores Odoo 14 bill name |
| 13 | `narration` / `comment` | `narration` | ✅ | Internal notes/comments |
| 14 | `invoice_line_ids` / `line_ids` | `invoice_line_ids` | ✅ | Invoice lines - migrated separately |
| 15 | `payment_term_id` / `invoice_payment_term_id` | `invoice_payment_term_id` | ✅ | Payment terms - mapped from purchase order |
| 16 | `fiscal_position_id` | `fiscal_position_id` | ✅ | Fiscal position - mapped from purchase order |
| 17 | `invoice_origin` | `invoice_origin` | ⚠️ | Not mapped - could be set from purchase order |
| 18 | `move_type` | `move_type` | ✅ | Set to 'in_invoice' or 'in_refund' |
| 19 | `purchase_id` | `purchase_id` | ✅ | **CRITICAL** - Links bill to purchase order |
| 20 | `create_date` | `create_date` | ✅ | Preserved via SQL update |
| 21 | `write_date` | `write_date` | ✅ | Preserved via SQL update |
| 22 | `create_uid` | `create_uid` | ✅ | Preserved via SQL update (user mapping) |
| 23 | `write_uid` | `write_uid` | ✅ | Preserved via SQL update (user mapping) |

---

## 2. Custom Fields - Odoo 19 (eq_fc_purchase_custom)

| # | Odoo 19 Field | Field Type | Status | Notes |
|---|---------------|------------|--------|-------|
| 1 | `quote_reference` | `Char` | ❌ | **NOT MIGRATED** - Quote reference from RFQ |
| 2 | `lpo_number` | `Char` | ❌ | **NOT MIGRATED** - Local Purchase Order number |
| 3 | `voucher_number` | `Char` | ❌ | **NOT MIGRATED** - Voucher number |
| 4 | `po_number` | `Char` | ⚠️ | Auto-set from `purchase_id.name` on create/onchange |
| 5 | `is_wo_header` | `Boolean` | ❌ | **NOT MIGRATED** - Invoice Without Header flag |
| 6 | `is_with_stamp` | `Boolean` | ❌ | **NOT MIGRATED** - With Stamp flag |

**Note:** `po_number` is automatically set from the purchase order name, so it's partially migrated.

---

## 3. Custom Fields - Odoo 14 (metro_erp module)

**Source:** `metro_erp/models/invoice.py` - `AccountMoveExtend` class

| # | Odoo 14 Field | Field Type | Odoo 19 Equivalent | Status | Notes |
|---|---------------|------------|-------------------|--------|-------|
| 1 | `location` | `Char` | N/A | ❌ | **NOT MIGRATED** - Location field (no equivalent in Odoo 19) |
| 2 | `site_name` | `Char` | N/A | ❌ | **NOT MIGRATED** - Site Name (no equivalent in Odoo 19) |
| 3 | `create_do` | `Boolean` | N/A | ❌ | **NOT MIGRATED** - Is DO flag (no equivalent in Odoo 19) |
| 4 | `picking_ids` | `Many2many` | N/A | ❌ | **NOT MIGRATED** - Delivery Details (no equivalent in Odoo 19) |
| 5 | `is_wo_header` | `Boolean` | `is_wo_header` | ❌ | **NOT MIGRATED** - Invoice Without Header |
| 6 | `bank_details` | `Text` | N/A | ❌ | **NOT MIGRATED** - Bank Details (no equivalent in Odoo 19) |
| 7 | `file_to_upload` | `Binary` | N/A | ❌ | **NOT MIGRATED** - File upload (no equivalent in Odoo 19) |
| 8 | `filename` | `Char` | N/A | ❌ | **NOT MIGRATED** - File Name (no equivalent in Odoo 19) |
| 9 | `is_with_stamp` | `Boolean` | `is_with_stamp` | ❌ | **NOT MIGRATED** - With Stamp |
| 10 | `voucher_no` | `Char` | `voucher_number` | ❌ | **NOT MIGRATED** - Voucher Number (field name differs) |
| 11 | `in_note` | `Text` | N/A | ❌ | **NOT MIGRATED** - Note (could map to `narration`?) |
| 12 | `lpo_n` | `Char` | `lpo_number` | ❌ | **NOT MIGRATED** - LPO number (field name differs) |
| 13 | `quote_reference` | `Many2one` | `quote_reference` | ❌ | **NOT MIGRATED** - Quote Reference (type differs: Many2one → Char) |
| 14 | `po_no` | `Char` | `po_number` | ⚠️ | **PARTIALLY MIGRATED** - PO Number (auto-set from purchase_id) |

**Key Findings:**
- **13 custom fields** found in Odoo 14 `metro_erp` module
- **6 fields** have direct equivalents in Odoo 19 (with name/type differences)
- **7 fields** have no equivalent in Odoo 19
- **0 fields** are currently being migrated

---

## 4. Custom Fields - Odoo 14 (Other Modules)

### 4.1 odx_purchase_generation
**Status:** ✅ **NO CUSTOM FIELDS ON account.move**
- This module only extends `purchase.order` and `purchase.order.line`
- No custom fields on `account.move`

### 4.2 odx_purchase_customisation
**Status:** ✅ **NO CUSTOM FIELDS ON account.move**
- This module only extends `purchase.order`, `purchase.order.line`, `project.project`, and `stock.picking`
- No custom fields on `account.move`

### 4.3 Other Potential Modules
The following modules were not checked but may have custom fields:
- `project_sale`
- `branch`
- `tis_sales_purchase_global_discount`

**Action Required:** Check these modules if needed.

---

## 5. Invoice Line Fields - account.move.line

| # | Odoo 14 Field | Odoo 19 Field | Status | Notes |
|---|---------------|---------------|--------|-------|
| 1 | `id` | N/A | ✅ | Used for identification |
| 2 | `product_id` | `product_id` | ✅ | Product - matched with purchase order line or by name |
| 3 | `name` | `name` | ✅ | Description |
| 4 | `quantity` | `quantity` | ✅ | Quantity |
| 5 | `price_unit` | `price_unit` | ✅ | Unit price |
| 6 | `discount` | `discount` | ✅ | Discount percentage |
| 7 | `tax_ids` | `tax_ids` | ✅ | Taxes - mapped by name |
| 8 | `account_id` | `account_id` | ✅ | Account - from product or journal default |
| 9 | `sequence` | `sequence` | ⚠️ | Not explicitly mapped |
| 10 | `purchase_line_id` | `purchase_line_id` | ⚠️ | Not explicitly mapped - could match with PO line |
| 11 | `purchase_order_id` | N/A | ✅ | Set via `move_id.purchase_id` |

---

## 6. Invoice Line Custom Fields

### 6.1 Odoo 14 (metro_erp) - account.move.line

| # | Odoo 14 Field | Field Type | Odoo 19 Equivalent | Status | Notes |
|---|---------------|------------|-------------------|--------|-------|
| 1 | `brand_id` | `Many2one` | N/A | ❌ | **NOT MIGRATED** - Brand field (no equivalent in Odoo 19) |

**Note:** The `brand_id` field is set via `_prepare_account_move_line()` in purchase order line, but it's not being migrated from Odoo 14 vendor bills.

---

## 7. Current Migration Implementation

### 7.1 Fields Fetched from Odoo 14

```python
bill_fields = [
    'id', 'name', 'partner_id', 'invoice_date', 'invoice_date_due', 'date_due',
    'state', 'amount_total', 'amount_untaxed', 'amount_tax', 'currency_id',
    'journal_id', 'ref', 'narration', 'comment', 'invoice_line_ids', 'line_ids',
    'payment_term_id', 'fiscal_position_id', 'invoice_origin', 'invoice_payment_term_id',
    'create_date', 'write_date', 'create_uid', 'write_uid'
]
```

**Missing Custom Fields from Odoo 14 (metro_erp):**
- `location`
- `site_name`
- `create_do`
- `picking_ids`
- `is_wo_header`
- `bank_details`
- `file_to_upload`
- `filename`
- `is_with_stamp`
- `voucher_no`
- `in_note`
- `lpo_n`
- `quote_reference`
- `po_no`

**Total Missing:** 14 custom fields from Odoo 14

### 7.2 Fields Mapped to Odoo 19

```python
bill_vals = {
    'move_type': move_type,  # 'in_invoice' or 'in_refund'
    'partner_id': partner.id,
    'purchase_id': purchase_order.id,  # CRITICAL: Links to purchase order
    'invoice_date': invoice_date,
    'journal_id': journal.id,
    'currency_id': currency.id,
    'ref': bill_name,  # Odoo 14 bill name
    'narration': narration,
    'invoice_payment_term_id': purchase_order.payment_term_id.id,
    'fiscal_position_id': purchase_order.fiscal_position_id.id,
}
```

**Missing Custom Fields in Odoo 19:**
- `quote_reference` (from Odoo 14: `quote_reference` - Many2one → Char conversion needed)
- `lpo_number` (from Odoo 14: `lpo_n`)
- `voucher_number` (from Odoo 14: `voucher_no`)
- `is_wo_header` (from Odoo 14: `is_wo_header`)
- `is_with_stamp` (from Odoo 14: `is_with_stamp`)

**Fields with No Odoo 19 Equivalent:**
- `location` (Odoo 14 only)
- `site_name` (Odoo 14 only)
- `create_do` (Odoo 14 only)
- `picking_ids` (Odoo 14 only)
- `bank_details` (Odoo 14 only)
- `file_to_upload` (Odoo 14 only)
- `filename` (Odoo 14 only)
- `in_note` (Odoo 14 only - could map to `narration`?)

---

## 8. Issues and Recommendations

### 8.1 Critical Issues

1. **Custom Fields Not Migrated** ❌ **CRITICAL**
   - **Odoo 19 custom fields** (`quote_reference`, `lpo_number`, `voucher_number`, `is_wo_header`, `is_with_stamp`) are not being migrated
   - **Odoo 14 custom fields** (14 fields from `metro_erp`) are not being fetched or migrated
   - **Impact:** Complete loss of all custom field data from both Odoo 14 and Odoo 19
   - **Recommendation:** 
     - Add all custom fields to `bill_fields` fetch list
     - Map Odoo 14 fields to Odoo 19 equivalents
     - Handle field name differences (`voucher_no` → `voucher_number`, `lpo_n` → `lpo_number`)
     - Handle field type differences (`quote_reference`: Many2one → Char)

3. **Bill State Not Properly Migrated** ⚠️
   - Bill state is only set via `action_post()` if state was 'posted'
   - Other states (draft, cancel) are not explicitly handled
   - **Recommendation:** Explicitly set state based on Odoo 14 state

### 8.2 Medium Priority Issues

1. **Invoice Origin Not Mapped** ⚠️
   - `invoice_origin` field is fetched but not mapped
   - **Recommendation:** Map from purchase order or Odoo 14 value

2. **Purchase Line Matching** ⚠️
   - Invoice lines don't explicitly link to purchase order lines via `purchase_line_id`
   - **Recommendation:** Match invoice lines with purchase order lines for better tracking

3. **Sequence Not Preserved** ⚠️
   - Line sequence is not explicitly mapped
   - **Recommendation:** Preserve line sequence from Odoo 14

### 8.3 Low Priority Issues

1. **Computed Fields** ⚠️
   - Amount fields are recomputed, which is correct, but initial values are not preserved
   - **Status:** Acceptable - recomputation ensures accuracy

---

## 9. Recommended Actions

### Priority 1: Add Custom Field Migration (CRITICAL)

1. **Add to `bill_fields` list in `_migrate_vendor_bills` method:**
   ```python
   bill_fields = [
       # ... existing fields ...
       # Add Odoo 14 custom fields from metro_erp
       'location', 'site_name', 'create_do', 'picking_ids',
       'is_wo_header', 'bank_details', 'file_to_upload', 'filename',
       'is_with_stamp', 'voucher_no', 'in_note', 'lpo_n',
       'quote_reference', 'po_no'
   ]
   ```

2. **Add to `bill_vals` mapping with field name conversion:**
   ```python
   # Map Odoo 14 custom fields to Odoo 19
   quote_ref_14 = bill_data.get('quote_reference')
   if isinstance(quote_ref_14, list) and len(quote_ref_14) > 0:
       # Many2one field - extract name
       quote_ref_name = quote_ref_14[1] if len(quote_ref_14) > 1 else ''
   else:
       quote_ref_name = str(quote_ref_14) if quote_ref_14 else ''
   
   bill_vals.update({
       'quote_reference': quote_ref_name,  # Many2one → Char
       'lpo_number': bill_data.get('lpo_n', ''),  # lpo_n → lpo_number
       'voucher_number': bill_data.get('voucher_no', ''),  # voucher_no → voucher_number
       'is_wo_header': bill_data.get('is_wo_header', False),
       'is_with_stamp': bill_data.get('is_with_stamp', False),
       # Note: po_number is auto-set from purchase_id, but can override
       'po_number': bill_data.get('po_no', '') or purchase_order.name,
   })
   
   # Map in_note to narration if narration is empty
   if not bill_vals.get('narration') and bill_data.get('in_note'):
       bill_vals['narration'] = bill_data.get('in_note', '')
   ```

3. **Handle fields with no Odoo 19 equivalent:**
   - `location`, `site_name`, `create_do`, `picking_ids`, `bank_details`, `file_to_upload`, `filename`
   - These can be stored in `narration` or logged for reference

### Priority 2: Improve State Migration

1. Explicitly handle all bill states (draft, posted, cancel)
2. Set state appropriately in Odoo 19

### Priority 3: Enhance Line Matching

1. Match invoice lines with purchase order lines
2. Set `purchase_line_id` on invoice lines
3. Preserve line sequence

---

## 10. Testing Checklist

- [ ] Standard fields migrate correctly
- [ ] Custom fields (Odoo 19) migrate correctly
- [ ] Custom fields (Odoo 14) migrate correctly (if any)
- [ ] Bill state is correctly set
- [ ] Invoice lines match purchase order lines
- [ ] Amounts are correctly calculated
- [ ] Dates are preserved
- [ ] Users are correctly mapped
- [ ] Bill links correctly to purchase order

---

## 11. Field Mapping Summary

| Category | Total Fields | Mapped | Not Mapped | Issues |
|----------|--------------|--------|------------|--------|
| Standard Header Fields | 23 | 18 | 5 | 0 |
| Custom Fields (Odoo 19) | 6 | 1 | 5 | 5 |
| Custom Fields (Odoo 14 - metro_erp) | 14 | 0 | 14 | 14 |
| Invoice Line Fields | 11 | 9 | 2 | 0 |
| Invoice Line Custom Fields (Odoo 14) | 1 | 0 | 1 | 1 |
| **TOTAL** | **55** | **28** | **27** | **20** |

**Migration Coverage:** 51% (28/55 fields)
**Critical Missing:** 27 fields (49% of total fields)

---

## 12. Conclusion

The current vendor bill migration implementation covers most standard fields but **misses ALL custom fields** from both Odoo 14 and Odoo 19. This is a **CRITICAL GAP** that results in **49% data loss** (27 out of 55 fields not migrated).

### Key Findings:

1. **Odoo 14 Custom Fields Found:**
   - **14 custom fields** in `metro_erp` module on `account.move`
   - **1 custom field** (`brand_id`) on `account.move.line`
   - **0 custom fields** in `odx_purchase_generation` and `odx_purchase_customisation` on `account.move`

2. **Field Mapping Status:**
   - **6 fields** have direct Odoo 19 equivalents (with name/type differences)
   - **8 fields** have no Odoo 19 equivalent
   - **0 fields** are currently being migrated

3. **Critical Missing Mappings:**
   - `voucher_no` (Odoo 14) → `voucher_number` (Odoo 19)
   - `lpo_n` (Odoo 14) → `lpo_number` (Odoo 19)
   - `quote_reference` (Odoo 14 Many2one) → `quote_reference` (Odoo 19 Char)
   - `is_wo_header` (Odoo 14) → `is_wo_header` (Odoo 19)
   - `is_with_stamp` (Odoo 14) → `is_with_stamp` (Odoo 19)
   - `po_no` (Odoo 14) → `po_number` (Odoo 19) - partially auto-set

**Immediate Action Required:**
1. ✅ **COMPLETED:** Investigated Odoo 14 modules - found 14 custom fields in `metro_erp`
2. ❌ **PENDING:** Add custom field fetching from Odoo 14 to `bill_fields` list
3. ❌ **PENDING:** Add custom field mapping to Odoo 19 with proper field name/type conversion
4. ❌ **PENDING:** Test migration with bills that have custom field values (e.g., Bill ID 17975)

---

**Document End**

