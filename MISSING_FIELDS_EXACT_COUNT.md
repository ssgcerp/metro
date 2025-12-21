# Exact Count of Missing Fields in Quotation (Sale Order)

## Summary
**Total Missing Fields: 20 fields** (from the main mapping table)

The "29+" count includes some fields that may be optional or need verification. Here's the exact breakdown:

---

## ✅ Confirmed Missing Fields (20 fields)

These are the fields marked as **MISSING** in the main field mapping table:

### 1. Financial Fields (1)
1. `currency_rate` - Float

### 2. AMC/Contract Fields (1)
2. `contract_id` - Many2one

### 3. Project/Work Fields (4)
3. `project_name` - Char
4. `scope_of_work` - Text
5. `engineer_name` - Char
6. `effective_date` - Date

### 4. Status/Flag Fields (7)
7. `safety_hse_quality` - Boolean
8. `is_warning` - Boolean
9. `is_tax_include` - Boolean
10. `is_reverse` - Boolean
11. `has_due` - Boolean
12. `require_payment` - Boolean
13. `show_update_pricelist` - Boolean
14. `quotation_reverse` - Boolean

### 5. Reference/ID Fields (4)
15. `medium_id` - Many2one
16. `source_id` - Many2one
17. `branch_id` - Many2one
18. `reference_drawing` - Char/Text

### 6. Other Fields (3)
19. `sale_order_option_ids` - One2many
20. `signature` - Binary/Text
21. `sale_oder_type` - Selection/Char (note: typo in Odoo 14)

---

## ⚠️ Additional Fields (May Need Verification)

These fields are mentioned in the detailed list but may need verification:

22. `date_start` - Date (might be standard Odoo field)
23. `lock_sale` - Boolean (might be standard Odoo field)

---

## 📊 Breakdown by Category

| Category | Count | Fields |
|----------|-------|--------|
| **Financial** | 1 | currency_rate |
| **AMC/Contract** | 1 | contract_id |
| **Project/Work** | 4 | project_name, scope_of_work, engineer_name, effective_date |
| **Status/Flags** | 8 | safety_hse_quality, is_warning, is_tax_include, is_reverse, has_due, require_payment, show_update_pricelist, quotation_reverse |
| **Reference/ID** | 4 | medium_id, source_id, branch_id, reference_drawing |
| **Other** | 3 | sale_order_option_ids, signature, sale_oder_type |
| **TOTAL** | **21** | (20 confirmed + 1 optional) |

---

## 🔍 Why "29+" was mentioned

The "29+" count in the original document included:
- All fields from the detailed missing fields list
- Some fields that might be standard Odoo fields
- Fields that need verification

**Actual confirmed missing: 20-21 fields**

---

## ✅ Fields That Already Exist (22 fields)

These don't need to be created:
- amount_discount, amount_total_with_discount, discount_type, discount_rate, amount_grand, retention_rate, is_tax_after_discount, analytic_id (from tis_sales_purchase_global_discount)
- is_amc, amc_estimation
- estimated_hours, project_id, description, is_completed, revision_id, estimation_id, work_location, subject, inclusion, exclusion, is_project_order, revised_quotation

---

## ⚠️ Fields Needing Name Mapping (9 fields)

These exist but with different names:
- is_direct_order → direct_order
- is_lumpsum → lumpsum
- is_with_stamp → with_stamp
- is_with_unit_price → with_unit_price
- is_with_uom → with_uom
- is_brand → with_brand
- attention → attention_id
- client → client_id
- consultants → consultants_ids
- regards → thanks_and_regards

---

## Next Steps

1. **Verify** if `date_start` and `lock_sale` are standard Odoo fields
2. **Prioritize** the 20 confirmed missing fields
3. **Create** field definitions for high-priority fields first
4. **Update** migration script with field mappings


