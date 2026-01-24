# Customer Invoice Field Mapping Table (Odoo 14 → Odoo 19)

This document maps fields between Odoo 14 and Odoo 19 for customer invoices (`account.move` with `move_type='out_invoice'` or `move_type='out_refund'`).

## Excel Columns → Odoo Fields

| Excel Column | Odoo 14 Field | Odoo 19 Field | Status | Notes |
|-------------|---------------|---------------|--------|-------|
| Number | `name` | `name` | ✅ Mapped | Invoice number |
| Voucher Number | `voucher_no` | `voucher_number` | ✅ Mapped | Custom field (metro_erp → eq_fc_purchase_custom) |
| Invoice Partner Name | `partner_id` | `partner_id` | ✅ Mapped | Customer/Partner |
| Invoice/Bill Date | `invoice_date` | `invoice_date` | ✅ Mapped | Standard field |
| Due Date | `invoice_date_due` | `invoice_date_due` | ✅ Mapped | Standard field |
| Status | `state` | `state` | ✅ Mapped | draft, posted, cancel |
| Payment Status | `payment_state` | `payment_state` | ✅ Mapped | not_paid, paid, partial, reversed, inbound_payment, outbound_payment |
| Company | `company_id` | `company_id` | ✅ Mapped | Standard field (may need branch mapping) |
| Quote Reference | `quote_reference` (Many2one) | `quote_reference` (Char) | ✅ Mapped | Odoo 14: Many2one to quotation.order, Odoo 19: Char |

## Standard Odoo Fields (account.move)

| Odoo 14 Field | Odoo 19 Field | Status | Notes |
|--------------|---------------|--------|-------|
| `id` | `id` | ✅ Mapped | Record ID |
| `name` | `name` | ✅ Mapped | Invoice number |
| `partner_id` | `partner_id` | ✅ Mapped | Customer/Partner |
| `invoice_date` | `invoice_date` | ✅ Mapped | Invoice date |
| `invoice_date_due` | `invoice_date_due` | ✅ Mapped | Due date |
| `state` | `state` | ✅ Mapped | draft, posted, cancel |
| `payment_state` | `payment_state` | ✅ Mapped | Payment status |
| `amount_total` | `amount_total` | ✅ Mapped | Total amount |
| `amount_untaxed` | `amount_untaxed` | ✅ Mapped | Untaxed amount |
| `amount_tax` | `amount_tax` | ✅ Mapped | Tax amount |
| `currency_id` | `currency_id` | ✅ Mapped | Currency |
| `journal_id` | `journal_id` | ✅ Mapped | Journal |
| `ref` | `ref` | ✅ Mapped | Reference |
| `narration` | `narration` | ✅ Mapped | Internal notes |
| `invoice_line_ids` | `invoice_line_ids` | ✅ Mapped | Invoice lines |
| `line_ids` | `line_ids` | ✅ Mapped | All move lines |
| `invoice_origin` | `invoice_origin` | ✅ Mapped | Origin (e.g., sale order name) |
| `invoice_payment_term_id` | `invoice_payment_term_id` | ✅ Mapped | Payment terms |
| `fiscal_position_id` | `fiscal_position_id` | ✅ Mapped | Fiscal position |
| `sale_id` | `sale_id` | ✅ Mapped | Linked sale order (if exists) |
| `invoice_line_ids.product_id` | `invoice_line_ids.product_id` | ✅ Mapped | Products |
| `invoice_line_ids.quantity` | `invoice_line_ids.quantity` | ✅ Mapped | Quantities |
| `invoice_line_ids.price_unit` | `invoice_line_ids.price_unit` | ✅ Mapped | Unit prices |
| `invoice_line_ids.tax_ids` | `invoice_line_ids.tax_ids` | ✅ Mapped | Taxes |
| `create_date` | `create_date` | ✅ Mapped | Creation date |
| `write_date` | `write_date` | ✅ Mapped | Last write date |
| `create_uid` | `create_uid` | ✅ Mapped | Created by user |
| `write_uid` | `write_uid` | ✅ Mapped | Last updated by user |

## Custom Fields from metro_erp (Odoo 14)

| Odoo 14 Field | Type | Odoo 19 Field | Status | Notes |
|--------------|------|---------------|--------|-------|
| `location` | Char | `location` | ✅ Mapped | Custom field (metro_erp → eq_fc_invoice_custom) |
| `site_name` | Char | `site_name` | ✅ Mapped | Custom field (metro_erp → eq_fc_invoice_custom) |
| `create_do` | Boolean | `create_do` | ✅ Mapped | Custom field (metro_erp → eq_fc_invoice_custom) |
| `picking_ids` | Many2many | `picking_ids` | ✅ Mapped | Standard field (stock.picking) |
| `is_wo_header` | Boolean | `is_wo_header` | ✅ Mapped | Custom field (metro_erp → eq_fc_purchase_custom, may be shared) |
| `bank_details` | Text | `bank_details` | ✅ Mapped | Custom field (metro_erp → eq_fc_invoice_custom) |
| `file_to_upload` | Binary | `file_to_upload` | ✅ Mapped | Custom field (metro_erp → eq_fc_invoice_custom) |
| `filename` | Char | `filename` | ✅ Mapped | Custom field (metro_erp → eq_fc_invoice_custom) |
| `is_with_stamp` | Boolean | `is_with_stamp` | ✅ Mapped | Custom field (metro_erp → eq_fc_purchase_custom, may be shared) |
| `voucher_no` | Char | `voucher_number` | ✅ Mapped | Custom field (metro_erp → eq_fc_purchase_custom, may be shared) |
| `in_note` | Text | `in_note` | ✅ Mapped | Custom field (metro_erp → eq_fc_invoice_custom) |
| `lpo_n` | Char | ❌ Not Available | ⚠️ Not Mapped | Only for vendor bills, not customer invoices |
| `quote_reference` | Many2one | `quote_reference` | ✅ Mapped | Odoo 14: Many2one to quotation.order, Odoo 19: Char (eq_fc_purchase_custom, may be shared) |
| `po_no` | Char | ❌ Not Available | ⚠️ Not Mapped | Only for vendor bills, not customer invoices |

## Custom Fields from eq_fc_invoice_custom (Odoo 19)

| Odoo 19 Field | Type | Status | Notes |
|--------------|------|--------|-------|
| `location` | Char | ✅ Available | Custom field for customer invoices |
| `site_name` | Char | ✅ Available | Custom field for customer invoices |
| `create_do` | Boolean | ✅ Available | Custom field for customer invoices |
| `bank_details` | Text | ✅ Available | Custom field for customer invoices |
| `file_to_upload` | Binary | ✅ Available | Custom field for customer invoices |
| `filename` | Char | ✅ Available | Custom field for customer invoices |
| `in_note` | Text | ✅ Available | Custom field for customer invoices |
| `amc_contract_id` | Many2one | ✅ Available | AMC Contract (filtered by customer) - NEW in Odoo 19 |

## Custom Fields from eq_fc_purchase_custom (Odoo 19) - May be shared

| Odoo 19 Field | Type | Status | Notes |
|--------------|------|--------|-------|
| `quote_reference` | Char | ✅ Available | May be available for customer invoices (check if shared) |
| `voucher_number` | Char | ✅ Available | May be available for customer invoices (check if shared) |
| `is_wo_header` | Boolean | ✅ Available | May be available for customer invoices (check if shared) |
| `is_with_stamp` | Boolean | ✅ Available | May be available for customer invoices (check if shared) |
| `lpo_number` | Char | ⚠️ Vendor Only | Only for vendor bills (in_invoice) |
| `po_number` | Char | ⚠️ Vendor Only | Only for vendor bills (in_invoice) |

## Invoice Line Fields (account.move.line)

| Odoo 14 Field | Odoo 19 Field | Status | Notes |
|--------------|---------------|--------|-------|
| `id` | `id` | ✅ Mapped | Record ID |
| `product_id` | `product_id` | ✅ Mapped | Product |
| `name` | `name` | ✅ Mapped | Description |
| `quantity` | `quantity` | ✅ Mapped | Quantity |
| `price_unit` | `price_unit` | ✅ Mapped | Unit price |
| `discount` | `discount` | ✅ Mapped | Discount |
| `tax_ids` | `tax_ids` | ✅ Mapped | Taxes |
| `account_id` | `account_id` | ✅ Mapped | Account |
| `sequence` | `sequence` | ✅ Mapped | Sequence |
| `sale_line_ids` | `sale_line_ids` | ✅ Mapped | Linked sale order lines |
| `brand_id` | ❌ Not Available | ⚠️ Not Mapped | Odoo 14: product.product.brand, Odoo 19: May not exist |

## Linking to Sales Orders

| Link Method | Odoo 14 | Odoo 19 | Status | Notes |
|------------|---------|---------|--------|-------|
| `sale_id` | ✅ Available | ✅ Available | ✅ Mapped | Direct link to sale.order |
| `invoice_origin` | ✅ Available | ✅ Available | ✅ Mapped | Contains sale order name |
| `invoice_line_ids.sale_line_ids` | ✅ Available | ✅ Available | ✅ Mapped | Links invoice lines to sale order lines |

## Summary

### ✅ Fields to Migrate (Available in Both)
- Standard fields: `name`, `partner_id`, `invoice_date`, `invoice_date_due`, `state`, `payment_state`, `amount_total`, `currency_id`, `journal_id`, `ref`, `narration`, `invoice_origin`, `invoice_payment_term_id`, `fiscal_position_id`, `sale_id`
- Custom fields from eq_fc_invoice_custom: `location`, `site_name`, `create_do`, `bank_details`, `file_to_upload`, `filename`, `in_note`
- Custom fields from eq_fc_purchase_custom (if shared): `voucher_number` (from `voucher_no`), `quote_reference` (Many2one → Char), `is_wo_header`, `is_with_stamp`
- Invoice lines: All standard fields
- Dates/Users: `create_date`, `write_date`, `create_uid`, `write_uid`

### ⚠️ Fields Not Available in Odoo 19
- `lpo_n` / `lpo_number` - Only for vendor bills
- `po_no` / `po_number` - Only for vendor bills
- `brand_id` on invoice lines - May not exist in Odoo 19

### 🆕 New Fields in Odoo 19 (Not in Odoo 14)
- `amc_contract_id` - AMC Contract selection (filtered by customer) - Can be set during migration if contract exists

### 🔗 Sales Order Linking
- Primary: Use `sale_id` field (Many2one to sale.order)
- Secondary: Use `invoice_origin` to find sale order by name
- Line-level: Use `invoice_line_ids.sale_line_ids` to link invoice lines to sale order lines

## Recommendations


1. **Quote Reference**: Extract name from Many2one in Odoo 14 and store as Char in Odoo 19 (if field exists and is shared)
2. **Sales Order Linking**: Search for sale order by `quote_reference` or `invoice_origin` if `sale_id` not available
3. **Custom Fields**: All major custom fields from metro_erp are available in eq_fc_invoice_custom - migrate all of them
4. **Invoice Lines**: Migrate all lines with products, quantities, prices, taxes, and accounts
5. **Payment Status**: Map Odoo 14 payment status to Odoo 19 payment_state values
6. **File Upload**: Migrate `file_to_upload` and `filename` if present in Odoo 14
7. **AMC Contract**: If `quote_reference` exists and matches an AMC contract, try to link `amc_contract_id` in Odoo 19
8. **Shared Fields**: Check if `voucher_number`, `is_wo_header`, `is_with_stamp`, `quote_reference` from eq_fc_purchase_custom are available for customer invoices (may need to verify in Odoo 19 instance)


