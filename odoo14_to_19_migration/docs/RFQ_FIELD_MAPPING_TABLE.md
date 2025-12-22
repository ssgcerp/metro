# RFQ Migration Field Mapping Table

## Overview
This document maps all fields from Odoo 14 Purchase Order (RFQ) to Odoo 19 Purchase Order, including custom fields from various modules.

---

## Purchase Order Header Fields (purchase.order)

### Standard Odoo Fields

| Odoo 14 Field | Odoo 19 Field | Type | Status | Notes |
|--------------|---------------|------|--------|-------|
| `id` | `id` | Integer | ✅ Mapped | Primary key |
| `name` | `name` | Char | ✅ Mapped | Order reference (e.g., MFS-RAK-3627) |
| `partner_id` | `partner_id` | Many2one | ✅ Mapped | Vendor/Supplier |
| `date_order` | `date_order` | Datetime | ✅ Mapped | Order date |
| `date_planned` | `date_planned` | Datetime | ✅ Mapped | Expected arrival date |
| `date_approve` | `date_approve` | Datetime | ✅ Mapped | Approval date |
| `state` | `state` | Selection | ✅ Mapped | Status (draft, sent, purchase, done, cancel) |
| `currency_id` | `currency_id` | Many2one | ✅ Mapped | **Defaults to AED if not found** |
| `picking_type_id` | `picking_type_id` | Many2one | ✅ Mapped | Receipt type (incoming) |
| `company_id` | `company_id` | Many2one | ✅ Mapped | Company |
| `user_id` | `user_id` | Many2one | ✅ Mapped | Purchaser/Buyer |
| `order_line` | `order_line` | One2many | ⚠️ **ISSUE** | **Product lines - Currently not migrating** |
| `invoice_ids` | `invoice_ids` | One2many | ❌ Not mapped | Vendor bills (not migrated) |
| `picking_ids` | `picking_ids` | One2many | ❌ Not mapped | Receipts (not migrated) |
| `notes` | `note` | Text | ✅ Mapped | Notes (Odoo 19 uses singular 'note') |
| `note` | `note` | Text | ✅ Mapped | Alternative field name |
| `origin` | `origin` | Char | ✅ Mapped | Source document reference |
| `create_date` | `create_date` | Datetime | ✅ Mapped | Creation date (preserved) |
| `write_date` | `write_date` | Datetime | ✅ Mapped | Last update date (preserved) |
| `create_uid` | `create_uid` | Many2one | ✅ Mapped | Created by user (mapped by login/name) |
| `write_uid` | `write_uid` | Many2one | ✅ Mapped | Last updated by user (mapped by login/name) |
| `incoterm_id` | `incoterm_id` | Many2one | ✅ Mapped | Incoterm (e.g., EXW, FOB) |
| `payment_term_id` | `payment_term_id` | Many2one | ✅ Mapped | Payment terms |
| `fiscal_position_id` | `fiscal_position_id` | Many2one | ✅ Mapped | Fiscal position |

---

### Custom Fields - metro_erp Module (Odoo 14) - **UH Metro ERP**

**Module**: `metro_erp` (Metro ERP / UH Metro ERP)  
**Author**: Siyad S  
**Version**: 14.0

| Odoo 14 Field | Odoo 19 Field | Type | Status | Notes |
|--------------|---------------|------|--------|-------|
| `attention` | `attention` | Char | ✅ Mapped | Attention person name |
| `attention_mobile_number` | `attention_mobile_number` | Char | ✅ Mapped | Mobile number |
| `attention_note` | `attention_note` | Text | ✅ Mapped | Attention note |
| `is_with_stamp` | `is_with_stamp` | Boolean | ✅ Mapped | With stamp checkbox |
| `is_wo_header` | `is_wo_header` | Boolean | ✅ Mapped | Invoice without header |
| `is_lumpsum` | `is_lumpsum` | Boolean | ✅ Mapped | Lumpsum checkbox |
| `internal_notes` | `internal_notes` | Text | ✅ Mapped | Remarks/Internal notes |
| `verified_by` | `verified_by` | Char | ✅ Mapped | Verified by person |
| `approved_by` | `approved_by` | Char | ✅ Mapped | Approved by person |
| `project_code` | `project_code` | Many2one | ✅ Mapped | Project code |
| `project` | `project` | Char | ✅ Mapped | Project name (computed from project_code) |
| `order_contact` | `order_contact` | Char | ✅ Mapped | Order contact person |
| `contact_no` | `contact_no` | Char | ✅ Mapped | Contact number |
| `supplier_quote_ref` | `supplier_quote_ref` | Char | ✅ Mapped | Supplier quotation reference |
| `delivery_address` | `delivery_address` | Char | ✅ Mapped | Delivery address |
| `revision_id` | ❌ Not in Odoo 19 | Many2one | ❌ Not mapped | Revision group (purchase.order.revision) |
| `revision_count` | ❌ Not in Odoo 19 | Integer (computed) | ❌ Not mapped | Number of revisions (computed) |
| `is_account_approval` | ❌ Not in Odoo 19 | Boolean | ❌ Not mapped | Account approval flag |
| `is_approval` | ❌ Not in Odoo 19 | Boolean | ❌ Not mapped | Quotation approval flag |
| `approval_id` | ❌ Not in Odoo 19 | Many2one | ❌ Not mapped | Approved by user (res.users) |
| `state` | `state` | Selection | ✅ Mapped | **Custom states**: draft='RFQ', sent='RFQ Sent', to approve, approval_pending, approve='Approved', purchase, done, cancel |

---

### Custom Fields - odx_purchase_customisation Module (Odoo 14)

| Odoo 14 Field | Odoo 19 Field | Type | Status | Notes |
|--------------|---------------|------|--------|-------|
| `sale_order_reference` | `sale_order_reference` | Char (computed) | ✅ Mapped | Related sale order references |
| `project_id` | `project_code` | Many2one | ✅ Mapped | **Mapped to project_code** (from odx_purchase_customisation or project_sale) |
| `is_synced` | ❌ Not in Odoo 19 | Boolean | ❌ Not mapped | Synced with project flag |
| `is_manually_sync` | ❌ Not in Odoo 19 | Boolean | ❌ Not mapped | Manual sync flag |
| `is_from_project` | ❌ Not in Odoo 19 | Boolean | ❌ Not mapped | From project flag |
| `project_id_related` | ❌ Not in Odoo 19 | Many2one (computed) | ❌ Not mapped | Computed project |

---

### Custom Fields - project_sale Module (Odoo 14)

| Odoo 14 Field | Odoo 19 Field | Type | Status | Notes |
|--------------|---------------|------|--------|-------|
| `projects_line` | `project_request_line_ids` | One2many | ❌ Not mapped | Project request lines (Projects tab) |
| `delivery_line` | `delivery_order_line_ids` | One2many | ❌ Not mapped | DO Details lines |
| `delivery_partner_id` | ❌ Not in Odoo 19 | Many2one | ❌ Not mapped | Customer/Delivery partner |
| `project_id` | `project_code` | Many2one | ✅ Mapped | **Mapped to project_code** (from odx_purchase_customisation or project_sale) |
| `is_from_project` | ❌ Not in Odoo 19 | Boolean | ❌ Not mapped | From project flag |

---

### Custom Fields - branch Module (Odoo 14)

| Odoo 14 Field | Odoo 19 Field | Type | Status | Notes |
|--------------|---------------|------|--------|-------|
| `branch_id` | `company_id` | Many2one | ✅ Mapped | **Mapped to company_id** (via branch_company_mapping) |

---

### Custom Fields - odx_purchase_generation Module (Odoo 14)

| Odoo 14 Field | Odoo 19 Field | Type | Status | Notes |
|--------------|---------------|------|--------|-------|
| `moved_order_line_ids` | ❌ Not in Odoo 19 | One2many | ❌ Not mapped | Moved order lines |

---

### Custom Fields - tis_sales_purchase_global_discount Module (Odoo 14)

| Odoo 14 Field | Odoo 19 Field | Type | Status | Notes |
|--------------|---------------|------|--------|-------|
| `discount_type` | ❌ Not in Odoo 19 | Selection | ❌ Not mapped | Discount type (percent/amount) |
| `discount_rate` | ❌ Not in Odoo 19 | Float | ❌ Not mapped | Discount rate |
| `discount_narration` | ❌ Not in Odoo 19 | Char | ❌ Not mapped | Discount narration |
| `retention_rate` | ❌ Not in Odoo 19 | Float | ❌ Not mapped | Retention rate |
| `amount_discount` | ❌ Not in Odoo 19 | Float (computed) | ❌ Not mapped | Discount amount |
| `is_tax_after_discount` | ❌ Not in Odoo 19 | Boolean | ❌ Not mapped | Tax after discount flag |

---

### Custom Fields - eq_fc_purchase_custom Module (Odoo 19)

**Note**: Most fields in this module also exist in `metro_erp` (Odoo 14). Fields marked with ⭐ are **new in Odoo 19** and don't exist in Odoo 14.

| Odoo 14 Field | Odoo 19 Field | Type | Status | Notes |
|--------------|---------------|------|--------|-------|
| `attention` (metro_erp) | `attention` | Char | ✅ Mapped | Attention person name |
| `delivery_address` (metro_erp) | `delivery_address` | Char | ✅ Mapped | Delivery address |
| `attention_mobile_number` (metro_erp) | `attention_mobile_number` | Char | ✅ Mapped | Mobile number |
| `is_with_stamp` (metro_erp) | `is_with_stamp` | Boolean | ✅ Mapped | With stamp checkbox |
| `is_wo_header` (metro_erp) | `is_wo_header` | Boolean | ✅ Mapped | Invoice without header |
| `is_lumpsum` (metro_erp) | `is_lumpsum` | Boolean | ✅ Mapped | Lumpsum checkbox |
| `attention_note` (metro_erp) | `attention_note` | Text | ✅ Mapped | Attention note |
| ⭐ ❌ Not in Odoo 14 | `ask_confirmation` | Boolean | ✅ Mapped | Ask confirmation checkbox (**NEW in Odoo 19**) |
| ⭐ ❌ Not in Odoo 14 | `receipt_date` | Datetime | ✅ Mapped | Expected receipt date (**NEW in Odoo 19**) |
| ⭐ ❌ Not in Odoo 14 | `deliver_to` | Many2one | ✅ Mapped | Deliver to location (**NEW in Odoo 19**) |
| `verified_by` (metro_erp) | `verified_by` | Char | ✅ Mapped | Verified by person |
| `approved_by` (metro_erp) | `approved_by` | Char | ✅ Mapped | Approved by person |
| `project_code` (metro_erp) | `project_code` | Many2one | ✅ Mapped | Project code |
| `project` (metro_erp) | `project` | Char (computed) | ✅ Mapped | Project name (computed from project_code) |
| `order_contact` (metro_erp) | `order_contact` | Char | ✅ Mapped | Order contact person |
| `contact_no` (metro_erp) | `contact_no` | Char | ✅ Mapped | Contact number |
| `supplier_quote_ref` (metro_erp) | `supplier_quote_ref` | Char | ✅ Mapped | Supplier quotation reference |
| `internal_notes` (metro_erp) | `internal_notes` | Text | ✅ Mapped | Remarks/Internal notes |
| `sale_order_reference` (odx_purchase_customisation) | `sale_order_reference` | Char (computed) | ✅ Mapped | Related sale order references |
| ⭐ ❌ Not in Odoo 14 | `billing_status` | Selection (computed) | ❌ Not mapped | Billing status (computed field, **NEW in Odoo 19**) |
| ⭐ ❌ Not in Odoo 14 | `project_request_line_ids` | One2many | ❌ Not mapped | Project request lines (Projects tab, **NEW in Odoo 19**) |
| ⭐ ❌ Not in Odoo 14 | `delivery_order_line_ids` | One2many | ❌ Not mapped | DO Details lines (**NEW in Odoo 19**) |

---

## Purchase Order Line Fields (purchase.order.line)

### Standard Odoo Fields

| Odoo 14 Field | Odoo 19 Field | Type | Status | Notes |
|--------------|---------------|------|--------|-------|
| `id` | `id` | Integer | ✅ Mapped | Primary key |
| `order_id` | `order_id` | Many2one | ✅ Mapped | Purchase order |
| `product_id` | `product_id` | Many2one | ✅ Mapped | Product |
| `name` | `name` | Char | ✅ Mapped | Description |
| `product_qty` | `product_qty` | Float | ✅ Mapped | Quantity |
| `product_uom` | `product_uom` | Many2one | ✅ Mapped | Unit of measure |
| `price_unit` | `price_unit` | Float | ✅ Mapped | Unit price |
| `discount` | `discount` | Float | ✅ Mapped | Discount |
| `taxes_id` | `taxes_id` | Many2many | ✅ Mapped | Taxes |
| `date_planned` | `date_planned` | Datetime | ✅ Mapped | Scheduled date |
| `sequence` | `sequence` | Integer | ✅ Mapped | Sequence/Order |

---

### Custom Fields - metro_erp Module (Odoo 14) - **UH Metro ERP**

| Odoo 14 Field | Odoo 19 Field | Type | Status | Notes |
|--------------|---------------|------|--------|-------|
| `brand_id` | `brand_id` | Many2one | ✅ Mapped | Product brand (product.product.brand) |
| `project_id` | `project_id` | Many2one | ✅ Mapped | Project |
| `customer_id` | `customer_id` | Many2one | ✅ Mapped | Customer |
| `project_orderline_id` | ❌ Not in Odoo 19 | Many2one | ❌ Not mapped | Project orderline link (project.project.orderline) |

---

### Custom Fields - branch Module (Odoo 14)

| Odoo 14 Field | Odoo 19 Field | Type | Status | Notes |
|--------------|---------------|------|--------|-------|
| `branch_id` | ❌ Not in Odoo 19 | Many2one (related) | ❌ Not mapped | Branch (related from order_id) |

---

### Custom Fields - eq_fc_purchase_custom Module (Odoo 19)

| Odoo 14 Field | Odoo 19 Field | Type | Status | Notes |
|--------------|---------------|------|--------|-------|
| ❌ Not in Odoo 14 | `brand_id` | Many2one | ✅ Mapped | Product brand |
| ❌ Not in Odoo 14 | `project_id` | Many2one | ✅ Mapped | Project |
| ❌ Not in Odoo 14 | `customer_id` | Many2one | ✅ Mapped | Customer |

---

## Field Mapping Summary

### ✅ Successfully Mapped Fields: 45+
- All standard Odoo fields
- All custom header fields from metro_erp
- All custom line fields (brand, project, customer)
- Currency defaults to AED
- Payment terms, fiscal position, incoterm

### ⚠️ Known Issues: 1
- **Product Lines (`order_line`)**: Currently not migrating - **CRITICAL ISSUE**

### ❌ Not Mapped Fields: 20+
- Revision tracking fields
- Approval workflow fields
- Branch fields
- Discount/retention fields
- Project request lines (one2many)
- DO Details lines (one2many)

---

## Current Migration Status

### ✅ Working
- RFQ header creation
- All custom header fields
- Currency mapping (defaults to AED)
- Vendor mapping
- Project mapping
- User/Purchaser mapping
- Payment terms, fiscal position, incoterm

### ⚠️ Not Working
- **Product Lines**: Lines are not being created in Odoo 19
  - Issue: `order_line` field migration failing
  - Impact: RFQs created without products
  - Status: Under investigation with enhanced logging

### 🔍 Debugging
Enhanced logging has been added to track:
- Whether `order_line` is fetched from Odoo 14
- Whether line IDs are extracted correctly
- Whether products are found/created
- Whether lines are created successfully
- Database vs memory line counts

---

## Migration Process Flow

1. **Fetch RFQ from Odoo 14** → Get all header fields
2. **Map Vendor** → Find/create vendor in Odoo 19
3. **Map Currency** → Default to AED if not found
4. **Map Purchaser** → Find user by login/name/email
5. **Create RFQ Header** → Create purchase.order in Odoo 19
6. **Fetch Order Lines** → Get `order_line` IDs from Odoo 14
7. **Migrate Each Line** → Create purchase.order.line for each
   - Find/create product
   - Map UoM, taxes, brand, project, customer
8. **Verify Migration** → Check line count in memory and database

---

## Notes

- **Computed Fields**: Fields marked as "computed" are not stored and may not be available during migration
- **One2many Fields**: Project request lines and DO details are not migrated (complex relationships)
- **Branch Fields**: Branch functionality may not exist in Odoo 19
- **Currency**: Always defaults to AED if original currency not found
- **Products**: Products are created if not found in Odoo 19 (by default_code or barcode)

---

## Last Updated
2025-12-22
