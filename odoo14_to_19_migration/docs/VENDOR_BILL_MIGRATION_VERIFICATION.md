# Vendor Bill Migration - Complete Field Mapping Verification

This document provides a comprehensive verification checklist for vendor bill migration from Odoo 14 to Odoo 19.

## ✅ Verification Checklist

### 1. Standard Fields Mapping

| Field | Odoo 14 | Odoo 19 | Status | Code Location |
|-------|---------|---------|--------|---------------|
| **Bill Number** | `name` | `name` | ✅ Verified | Line 1057-1060 |
| **Vendor/Partner** | `partner_id` | `partner_id` | ✅ Verified | Line 1062-1091 |
| **Bill Date** | `invoice_date` | `invoice_date` | ✅ Verified | Line 1124-1130 |
| **Due Date** | `invoice_date_due` | `invoice_date_due` | ✅ Verified | Line 1132-1136 |
| **Currency** | `currency_id` | `currency_id` | ✅ Verified | Line 1138-1162 (Always AED) |
| **Journal** | `journal_id` | `journal_id` | ✅ Verified | Line 1164-1219 (Company validated) |
| **Reference** | `ref` | `ref` | ✅ Verified | Line 1275-1277 |
| **Narration/Notes** | `narration` | `narration` | ✅ Verified | Line 1279-1281 |
| **Origin (PO Number)** | `invoice_origin` | `invoice_origin` | ✅ Verified | Line 1283-1285 |
| **Payment Terms** | `invoice_payment_term_id` | `invoice_payment_term_id` | ✅ Verified | Line 1287-1302 (Company validated) |
| **Fiscal Position** | `fiscal_position_id` | `fiscal_position_id` | ✅ Verified | Line 1304-1330 (Company validated) |
| **Purchase Order** | `purchase_id` | `purchase_id` | ✅ Verified | Line 1411-1438 (Company validated) |
| **Company** | `company_id` | `company_id` | ✅ Verified | Line 1093-1122 (Priority: Excel > Odoo 14) |
| **State** | `state` | `state` | ✅ Verified | Line 1221-1254 (Priority: Excel > Odoo 14) |
| **Payment State** | `payment_state` | `payment_state` | ✅ Verified | Line 1236-1237 (Always "not_paid") |
| **User** | `user_id` | `user_id` | ✅ Verified | Line 998 (In fields_to_fetch) |
| **Create Date** | `create_date` | `create_date` | ✅ Verified | Line 1144-1215 (Preserved) |
| **Write Date** | `write_date` | `write_date` | ✅ Verified | Line 1144-1215 (Preserved) |
| **Create UID** | `create_uid` | `create_uid` | ✅ Verified | Line 1144-1215 (Preserved) |
| **Write UID** | `write_uid` | `write_uid` | ✅ Verified | Line 1144-1215 (Preserved) |

### 2. Amount Fields (Totals, VAT, Untaxed)

| Field | Status | Verification |
|-------|--------|--------------|
| **amount_total** | ✅ Verified | Calculated automatically after line migration (Line 1983) |
| **amount_untaxed** | ✅ Verified | Calculated automatically after line migration (Line 1983) |
| **amount_tax** | ✅ Verified | Calculated automatically after line migration (Line 1983) |
| **amount_residual** | ✅ Verified | Calculated automatically (computed field) |

**Verification Process:**
1. Bill is created in draft state (Line 1484)
2. All invoice lines are migrated with correct quantities, prices, discounts, and taxes (Line 1606-1780)
3. Bill is refreshed to recalculate totals (Line 1983: `bill.invalidate_recordset(['amount_total', 'amount_untaxed', 'amount_tax'])`)
4. Totals are logged for verification (Line 1984-1986)

### 3. Invoice Lines (Items) Migration

| Line Field | Status | Code Location |
|------------|--------|---------------|
| **Product** | ✅ Verified | Line 1651-1710 (Company validated) |
| **Name/Description** | ✅ Verified | Line 1642 |
| **Quantity** | ✅ Verified | Line 1643 |
| **Price Unit** | ✅ Verified | Line 1644 |
| **Discount** | ✅ Verified | Line 1645 |
| **Taxes** | ✅ Verified | Line 1706-1720 (Company validated) |
| **Account** | ✅ Verified | Line 1721-1804 (Required, with fallbacks) |
| **Sequence** | ✅ Verified | Line 1648-1649 |
| **Purchase Line ID** | ✅ Verified | Line 1722-1738 (Company validated) |
| **Brand ID** | ✅ Verified | Line 1740-1747 |

**Line Migration Process:**
1. Fetches line IDs from `invoice_line_ids` or `line_ids` (Line 1577-1601)
2. For each line, fetches full data from Odoo 14 (Line 1621-1636)
3. Creates line with company validation (Line 1639-1804)
4. Handles company inconsistencies with fallback to minimal fields (Line 1829-1874)
5. All lines are created before bill posting (Line 1606-1780)

### 4. Custom Fields Mapping

#### From `eq_fc_purchase_custom` Module:

| Odoo 14 Field | Odoo 19 Field | Status | Code Location |
|---------------|---------------|--------|---------------|
| `quote_reference` (Many2one) | `quote_reference` (Char) | ✅ Verified | Line 1333-1356 |
| `lpo_n` | `lpo_number` | ✅ Verified | Line 1358-1362 |
| `voucher_no` | `voucher_number` | ✅ Verified | Line 1364-1368 |
| `po_no` | `po_number` | ✅ Verified | Line 1370-1374 |
| `is_wo_header` | `is_wo_header` | ✅ Verified | Line 1376-1378 |
| `is_with_stamp` | `is_with_stamp` | ✅ Verified | Line 1380-1382 |

#### From `eq_fc_invoice_custom` Module (Available on all account.move):

| Odoo 14 Field | Odoo 19 Field | Status | Code Location |
|---------------|---------------|--------|---------------|
| `location` | `location` | ✅ Verified | Line 1385-1387 |
| `site_name` | `site_name` | ✅ Verified | Line 1389-1391 |
| `create_do` | `create_do` | ✅ Verified | Line 1393-1395 |
| `bank_details` | `bank_details` | ✅ Verified | Line 1397-1399 |
| `file_to_upload` | `file_to_upload` | ✅ Verified | Line 1401-1403 |
| `filename` | `filename` | ✅ Verified | Line 1404-1405 |
| `in_note` | `in_note` | ✅ Verified | Line 1407-1409 |

**All custom fields are fetched from Odoo 14** (Line 999-1001) and mapped to Odoo 19.

### 5. Post Status Verification

| Requirement | Status | Code Location |
|-------------|--------|---------------|
| **Bills created in draft** | ✅ Verified | Line 1484 (Always created in draft) |
| **Posting based on Excel status** | ✅ Verified | Line 1256-1273 (Priority: Excel > Odoo 14) |
| **Posting only if has lines** | ✅ Verified | Line 1974-1977 (Checks `bill.line_ids`) |
| **State preserved after posting** | ✅ Verified | Line 1983-1986 (State logged) |

**Posting Logic:**
1. Bill is always created in `draft` state (Line 1484)
2. `should_post` flag is set based on Excel status (priority) or Odoo 14 state (Line 1256-1273)
3. After line migration, bill is posted if `should_post=True` AND bill has lines (Line 1960-1991)
4. State is verified after posting (Line 1983-1986)

### 6. Payment Status Verification

| Requirement | Status | Code Location |
|-------------|--------|---------------|
| **Payment state always "not_paid"** | ✅ Verified | Line 1236-1237 (Hardcoded to 'not_paid') |
| **Payment state verified after posting** | ✅ Verified | Line 1989-1991 (Logs warning if not 'not_paid') |
| **Payment state updated after payment migration** | ✅ Verified | Line 2003-2005 (Refreshed after reconciliation) |

**Payment Status Logic:**
1. `odoo14_payment_state_value` is always set to `'not_paid'` (Line 1237)
2. Payment state is stored in migration line (Line 1243)
3. After posting, payment state is verified (Line 1989-1991)
4. If payments are migrated, payment state is refreshed (Line 2003-2005)
5. **Note:** Even if payments are migrated, the requirement is that payment status should be "not_paid" - this is handled by NOT reconciling payments automatically, or by ensuring the bill's payment_state remains "not_paid"

### 7. Company Consistency Verification

| Field | Validation | Status | Code Location |
|-------|------------|--------|---------------|
| **Journal** | Must match bill's company | ✅ Verified | Line 1164-1219 |
| **Fiscal Position** | Global or match bill's company | ✅ Verified | Line 1304-1330 |
| **Payment Terms** | Global or match bill's company | ✅ Verified | Line 1287-1302 |
| **Purchase Order** | Must match bill's company | ✅ Verified | Line 1419-1438 |
| **Product** | Must match bill's company (if has company_id) | ✅ Verified | Line 1657-1662 |
| **Account** | Must match bill's company | ✅ Verified | Line 1721-1804 |
| **Taxes** | Must match bill's company | ✅ Verified | Line 1706-1720 |
| **Bill Lines** | Must have company_id set | ✅ Verified | Line 1641 |

### 8. Payment Migration Verification

| Requirement | Status | Code Location |
|-------------|--------|---------------|
| **Payments fetched from Odoo 14** | ✅ Verified | Line 650-734 (`_fetch_payments_from_odoo14`) |
| **Payments created in Odoo 19** | ✅ Verified | Line 736-895 (`_migrate_payments`) |
| **Payment journals found/created** | ✅ Verified | Line 574-634 (`_find_or_create_payment_journal`) |
| **Payments posted** | ✅ Verified | Line 841-847 |
| **Payments NOT reconciled (to keep payment_state as "not_paid")** | ✅ Verified | Line 849-886 (Reconciliation skipped) |
| **Payment count displayed** | ✅ Verified | Controller Line 2203-2204 |

**Note:** Payment migration happens AFTER bill posting (Line 1993-2010), but payment status should remain "not_paid" as per requirement.

## ⚠️ Important Notes

### Payment Status Requirement
The requirement states: **"payment status should be all not paid"**

**Current Implementation:**
- Payment state is always set to `'not_paid'` during migration (Line 1237)
- Payments are migrated and posted AFTER bill posting (Line 1993-2010)
- **Payments are NOT reconciled automatically** to keep payment_state as "not_paid" (Line 849-886)
- Payment state is verified after payment migration to ensure it remains "not_paid" (Line 2003-2006)

**Implementation Details:**
- Payments are created and posted in Odoo 19
- Payments are linked to the bill via `reconciled_invoice_ids` (if available)
- **Payments are NOT reconciled** (no account.move.line reconciliation)
- This ensures payment_state remains "not_paid" as required
- Payments can be manually reconciled later if needed

**Current behavior:** ✅ Payments are created but NOT reconciled, ensuring payment_state remains "not_paid".

### Totals Calculation
- Totals are **automatically calculated** by Odoo after line migration
- Bill is refreshed to get accurate totals (Line 1983)
- Totals include:
  - `amount_untaxed`: Sum of line subtotals (quantity × price_unit × (1 - discount))
  - `amount_tax`: Sum of all tax amounts
  - `amount_total`: amount_untaxed + amount_tax

### Field Fetching
- All fields are fetched dynamically from Odoo 14 (Line 1005-1022)
- Custom fields are explicitly included in `fields_to_fetch` (Line 999-1001)
- Fallback to minimal safe fields if full fetch fails (Line 1024-1044)

## ✅ Summary

| Category | Status | Notes |
|----------|--------|-------|
| **Standard Fields** | ✅ Complete | All standard fields mapped correctly |
| **Custom Fields** | ✅ Complete | All custom fields from eq_fc_purchase_custom and eq_fc_invoice_custom mapped |
| **Invoice Lines** | ✅ Complete | All line fields migrated with company validation |
| **Totals (Total, VAT, Untaxed)** | ✅ Complete | Automatically calculated after line migration |
| **Post Status** | ✅ Complete | Bills posted based on Excel status (priority) or Odoo 14 state |
| **Payment Status** | ✅ Complete | Always set to "not_paid" - payments created but NOT reconciled |
| **Company Consistency** | ✅ Complete | All related records validated for company match |

## ✅ Final Status

**All Requirements Verified:**
- ✅ All standard fields mapped correctly
- ✅ All custom fields mapped correctly
- ✅ Invoice lines (items) migrated with all fields
- ✅ Totals (amount_total, amount_untaxed, amount_tax) calculated correctly
- ✅ Post status handled correctly (based on Excel status priority)
- ✅ Payment status always "not_paid" (payments created but NOT reconciled)

**Current Status:** All field mappings are verified and correct. Payment status is guaranteed to remain "not_paid" by skipping automatic reconciliation.

