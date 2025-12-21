# Sale Order Field Mapping Analysis: Odoo 14 to Odoo 19

## Overview
This document analyzes custom fields from Odoo 14 quotations and maps them to Odoo 19 equivalents, identifying missing fields that need to be created.

## Field Mapping Table

| Odoo 14 Field Name | Odoo 19 Field Name | Status | Notes |
|-------------------|-------------------|--------|-------|
| `amount_discount` | `amount_discount` | ✅ Exists | Same name (from tis_sales_purchase_global_discount) |
| `safety_hse_quality` | ❌ **MISSING** | Not Found | Needs to be created |
| `contract_id` | ❌ **MISSING** | Not Found | Needs to be created |
| `estimated_hours` | `estimated_hours` | ✅ Exists | Same name |
| `is_direct_order` | `direct_order` | ⚠️ **RENAMED** | Different name - needs mapping |
| `medium_id` | ❌ **MISSING** | Not Found | Needs to be created |
| `is_warning` | ❌ **MISSING** | Not Found | Needs to be created |
| `sale_order_option_ids` | ❌ **MISSING** | Not Found | Needs to be created |
| `reference_drawing` | ❌ **MISSING** | Not Found | Needs to be created |
| `discount_type` | `discount_type` | ✅ Exists | Same name (from tis_sales_purchase_global_discount) |
| `is_lumpsum` | `lumpsum` | ⚠️ **RENAMED** | Different name - needs mapping |
| `is_amc` | `is_amc` | ✅ Exists | Same name |
| `project_name` | ❌ **MISSING** | Not Found | Needs to be created |
| `signature` | ❌ **MISSING** | Not Found | Needs to be created |
| `retention_rate` | `retention_rate` | ✅ Exists | Same name (from tis_sales_purchase_global_discount) |
| `quotation_reverse` | ❌ **MISSING** | Not Found | Needs to be created |
| `source_id` | ❌ **MISSING** | Not Found | Needs to be created |
| `currency_rate` | ❌ **MISSING** | Not Found | Needs to be created |
| `project_id` | `project_id` | ✅ Exists | Same name |
| `amount_total_with_discount` | `amount_total_with_discount` | ✅ Exists | Same name (from tis_sales_purchase_global_discount) |
| `is_with_stamp` | `with_stamp` | ⚠️ **RENAMED** | Different name - needs mapping |
| `is_tax_include` | ❌ **MISSING** | Not Found | Needs to be created |
| `is_reverse` | ❌ **MISSING** | Not Found | Needs to be created |
| `description` | `description` | ✅ Exists | Same name |
| `is_completed` | `is_completed` | ✅ Exists | Same name (from revision module) |
| `is_with_unit_price` | `with_unit_price` | ⚠️ **RENAMED** | Different name - needs mapping |
| `scope_of_work` | ❌ **MISSING** | Not Found | Needs to be created |
| `branch_id` | ❌ **MISSING** | Not Found | Needs to be created |
| `is_with_uom` | `with_uom` | ⚠️ **RENAMED** | Different name - needs mapping |
| `effective_date` | ❌ **MISSING** | Not Found | Needs to be created |
| `amc_estimation` | `amc_estimation` | ✅ Exists | Same name |
| `show_update_pricelist` | ❌ **MISSING** | Not Found | Needs to be created |
| `consultants` | `consultants_ids` | ⚠️ **RENAMED** | Different name - needs mapping |
| `revision_id` | `revision_id` | ✅ Exists | Same name (from revision module) |
| `discount_rate` | `discount_rate` | ✅ Exists | Same name (from tis_sales_purchase_global_discount) |
| `require_payment` | ❌ **MISSING** | Not Found | Needs to be created |
| `analytic_id` | `analytic_id` | ✅ Exists | Same name (from tis_sales_purchase_global_discount) |
| `has_due` | ❌ **MISSING** | Not Found | Needs to be created |
| `amount_grand` | `amount_grand` | ✅ Exists | Same name (from tis_sales_purchase_global_discount) |
| `estimation_id` | `estimation_id` | ✅ Exists | Same name |
| `sale_oder_type` | ❌ **MISSING** | Not Found | Needs to be created (note: typo in Odoo 14) |
| `work_location` | `work_location` | ✅ Exists | Same name |
| `is_brand` | `with_brand` | ⚠️ **RENAMED** | Different name - needs mapping |
| `subject` | `subject` | ✅ Exists | Same name |
| `inclusion` | `inclusion` | ✅ Exists | Same name |
| `exclusion` | `exclusion` | ✅ Exists | Same name |
| `engineer_name` | ❌ **MISSING** | Not Found | Needs to be created |
| `is_project_order` | `is_project_order` | ✅ Exists | Same name |
| `is_tax_after_discount` | `is_tax_after_discount` | ✅ Exists | Same name (from tis_sales_purchase_global_discount) |
| `attention` | `attention_id` | ⚠️ **RENAMED** | Changed from Char to Many2one - needs mapping |
| `client` | `client_id` | ⚠️ **RENAMED** | Changed from Char to Many2one - needs mapping |
| `revised_quotation` | `revised_quotation` | ✅ Exists | Same name |
| `regards` | `thanks_and_regards` | ⚠️ **RENAMED** | Different name - needs mapping |

## Summary Statistics

- **Total Custom Fields in Odoo 14**: 60+ fields
- **Fields Already Exist in Odoo 19**: 22 fields (updated: added discount fields from `tis_sales_purchase_global_discount`)
- **Fields with Different Names (Need Mapping)**: 9 fields
- **Missing Fields (Need to Create)**: 29+ fields (updated: removed discount-related fields)

## Missing Fields List (Need to be Created in Odoo 19)

### Financial/Discount Fields
1. ~~`amount_discount`~~ - ✅ **EXISTS** in Odoo 19 (from tis_sales_purchase_global_discount)
2. ~~`amount_total_with_discount`~~ - ✅ **EXISTS** in Odoo 19 (from tis_sales_purchase_global_discount)
3. ~~`discount_type`~~ - ✅ **EXISTS** in Odoo 19 (from tis_sales_purchase_global_discount)
4. ~~`discount_rate`~~ - ✅ **EXISTS** in Odoo 19 (from tis_sales_purchase_global_discount)
5. ~~`amount_grand`~~ - ✅ **EXISTS** in Odoo 19 (from tis_sales_purchase_global_discount)
6. ~~`retention_rate`~~ - ✅ **EXISTS** in Odoo 19 (from tis_sales_purchase_global_discount)
7. `currency_rate` - Float

### AMC/Contract Fields
8. ~~`is_amc`~~ - ✅ **EXISTS** in Odoo 19 (Boolean)
9. `contract_id` - Many2one (likely to amc.contract or similar)
10. ~~`amc_estimation`~~ - ✅ **EXISTS** in Odoo 19 (Many2one/Char)

### Project/Work Fields
11. `project_name` - Char
12. `scope_of_work` - Text
13. `engineer_name` - Char
14. `effective_date` - Date
15. `date_start` - Date (if custom, not standard)

### Status/Flag Fields
16. `safety_hse_quality` - Boolean
17. `is_warning` - Boolean
18. `is_tax_include` - Boolean
19. `is_reverse` - Boolean
20. ~~`is_tax_after_discount`~~ - ✅ **EXISTS** in Odoo 19 (from tis_sales_purchase_global_discount)
21. `has_due` - Boolean
22. `require_payment` - Boolean
23. `show_update_pricelist` - Boolean
24. `quotation_reverse` - Boolean

### Reference/ID Fields
25. `medium_id` - Many2one
26. `source_id` - Many2one
27. `branch_id` - Many2one
28. ~~`analytic_id`~~ - ✅ **EXISTS** in Odoo 19 (from tis_sales_purchase_global_discount)
29. `reference_drawing` - Char/Text

### Other Fields
30. `sale_order_option_ids` - One2many
31. `signature` - Binary/Text
32. `sale_oder_type` - Selection/Char (note: typo in original)
33. `lock_sale` - Boolean (if custom, not standard)

## Field Name Mappings (Odoo 14 → Odoo 19)

| Odoo 14 | Odoo 19 | Type Change |
|---------|---------|-------------|
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

## Migration Recommendations

### Priority 1: Critical Business Fields
These fields are likely critical for business operations:
- ~~`is_amc`~~ - ✅ Already exists in Odoo 19
- `contract_id` - Contract linking
- ~~`amount_discount`, `discount_rate`, `discount_type`~~ - ✅ Already exists (from tis_sales_purchase_global_discount)
- `branch_id` - Branch/company identification
- `source_id` - Lead source tracking
- `sale_oder_type` - Order type classification

### Priority 2: Financial Fields
- ~~`amount_total_with_discount`~~ - ✅ Already exists (from tis_sales_purchase_global_discount)
- ~~`amount_grand`~~ - ✅ Already exists (from tis_sales_purchase_global_discount)
- ~~`retention_rate`~~ - ✅ Already exists (from tis_sales_purchase_global_discount)
- `currency_rate` - Currency conversion rate

### Priority 3: Additional Features
- `safety_hse_quality` - Safety/Quality flag
- `is_warning` - Warning flag
- `signature` - Digital signature
- `reference_drawing` - Drawing reference
- `scope_of_work` - Work scope details
- `engineer_name` - Engineer assignment

## Next Steps

1. **Review each missing field** to determine:
   - Field type (Char, Float, Boolean, Many2one, etc.)
   - Related model (if Many2one)
   - Default values
   - Required/optional status

2. **Create field definitions** in the appropriate model file:
   - `fm_amc_crm_custom/models/sale_order_extended.py` (main file)

3. **Update migration script** to handle:
   - Field name mappings (renamed fields)
   - Data type conversions (Char → Many2one)
   - Default values for missing data

4. **Test migration** with sample data to ensure all fields are properly mapped

## Notes

- Some fields may be standard Odoo fields that were not listed in the custom fields
- Some fields might have been deprecated or replaced with different functionality
- Field types should be verified against actual Odoo 14 database schema
- Consider creating computed fields for calculated values like `amount_total_with_discount`


