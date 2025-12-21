# Remaining Pending Fields for Odoo 14 to 19 Migration

## Summary
After adding the `tis_sales_purchase_global_discount` module, **8 discount-related fields** are now available in Odoo 19.

**Current Status:**
- ✅ **22 fields already exist** in Odoo 19
- ⚠️ **9 fields need name mapping** (renamed fields)
- ❌ **29+ fields still need to be created**

---

## ✅ Fields Now Available (from tis_sales_purchase_global_discount)

The following discount-related fields are now available in Odoo 19:

1. ✅ `amount_discount` - Float/Monetary (computed)
2. ✅ `amount_total_with_discount` - Float/Monetary (computed)
3. ✅ `discount_type` - Selection (percent/amount)
4. ✅ `discount_rate` - Float
5. ✅ `amount_grand` - Float/Monetary (computed)
6. ✅ `retention_rate` - Float
7. ✅ `is_tax_after_discount` - Boolean
8. ✅ `analytic_id` - Many2one (account.analytic.account)

---

## ❌ Still Missing Fields (29+ fields to create)

### Financial Fields (1 field)
1. `currency_rate` - Float (Currency conversion rate)

### AMC/Contract Fields (1 field)
2. `contract_id` - Many2one (likely to amc.contract or similar)

### Project/Work Fields (5 fields)
3. `project_name` - Char
4. `scope_of_work` - Text
5. `engineer_name` - Char
6. `effective_date` - Date
7. `date_start` - Date (if custom, not standard)

### Status/Flag Fields (8 fields)
8. `safety_hse_quality` - Boolean
9. `is_warning` - Boolean
10. `is_tax_include` - Boolean
11. `is_reverse` - Boolean
12. `has_due` - Boolean
13. `require_payment` - Boolean
14. `show_update_pricelist` - Boolean
15. `quotation_reverse` - Boolean

### Reference/ID Fields (5 fields)
16. `medium_id` - Many2one
17. `source_id` - Many2one
18. `branch_id` - Many2one
19. `reference_drawing` - Char/Text

### Other Fields (9+ fields)
20. `sale_order_option_ids` - One2many
21. `signature` - Binary/Text
22. `sale_oder_type` - Selection/Char (note: typo in Odoo 14)
23. `lock_sale` - Boolean (if custom, not standard)

---

## ⚠️ Fields Needing Name Mapping (9 fields)

These fields exist in Odoo 19 but with different names. Migration script needs to map:

| Odoo 14 Field | Odoo 19 Field | Type Change |
|--------------|--------------|-------------|
| `is_direct_order` | `direct_order` | Boolean → Boolean |
| `is_lumpsum` | `lumpsum` | Boolean → Boolean |
| `is_with_stamp` | `with_stamp` | Boolean → Boolean |
| `is_with_unit_price` | `with_unit_price` | Boolean → Boolean |
| `is_with_uom` | `with_uom` | Boolean → Boolean |
| `is_brand` | `with_brand` | Boolean → Boolean |
| `attention` | `attention_id` | Char → Many2one |
| `client` | `client_id` | Char → Many2one |
| `consultants` | `consultants_ids` | Char → Many2many |
| `regards` | `thanks_and_regards` | Char → Text |

---

## Priority Recommendations

### 🔴 High Priority (Critical Business Fields)
1. `contract_id` - Contract linking (AMC functionality)
2. `branch_id` - Branch/company identification
3. `source_id` - Lead source tracking
4. `sale_oder_type` - Order type classification

### 🟡 Medium Priority (Financial/Operational)
5. `currency_rate` - Currency conversion
6. `scope_of_work` - Work scope details
7. `engineer_name` - Engineer assignment
8. `effective_date` - Effective date tracking

### 🟢 Low Priority (Additional Features)
9. `safety_hse_quality` - Safety/Quality flag
10. `is_warning` - Warning flag
11. `signature` - Digital signature
12. `reference_drawing` - Drawing reference
13. `project_name` - Project name
14. `date_start` - Start date
15. Other status flags and optional fields

---

## Next Steps

1. **Review and prioritize** which fields are actually needed for your business
2. **Create field definitions** in `fm_amc_crm_custom/models/sale_order_extended.py`
3. **Update migration script** to handle:
   - Field name mappings (9 renamed fields)
   - Data type conversions (Char → Many2one)
   - Default values for missing data
4. **Test migration** with sample data

---

## Notes

- The `tis_sales_purchase_global_discount` module provides comprehensive discount functionality
- Some fields might be standard Odoo fields that weren't in the custom fields list
- Field types should be verified against actual Odoo 14 database schema
- Consider creating computed fields for calculated values


