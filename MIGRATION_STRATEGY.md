# Migration Strategy: Field Creation Priority

## Approach
**Skip non-critical fields** and handle them during migration. Only create fields that are:
1. **Critical** for business operations
2. **Required** for data integrity
3. **Referenced** by other modules/functionality

---

## ✅ Fields to Create NOW (Before Migration)

### High Priority - Critical Business Fields (5 fields)
These are essential for core functionality:

1. **`contract_id`** - Many2one
   - **Why**: Critical for AMC functionality, likely referenced by other modules
   - **Type**: Many2one('amc.contract') - ✅ Confirmed: Model exists in amc_contracts module

2. **`branch_id`** - Many2one
   - **Why**: Branch/company identification - likely used for filtering/reporting
   - **Type**: Many2one('res.company') - ✅ Confirmed: Same as amc_contract module uses

3. **`source_id`** - Many2one
   - **Why**: Lead source tracking - important for CRM/sales analytics
   - **Type**: Many2one('utm.source') - Standard Odoo UTM module field

4. **`sale_oder_type`** - Selection/Char
   - **Why**: Order type classification - used for filtering/grouping
   - **Type**: Selection or Char (note: typo in Odoo 14 name)

5. **`currency_rate`** - Float
   - **Why**: Currency conversion - needed if multi-currency operations
   - **Type**: Float

---

## ⏸️ Fields to Skip/Create During Migration (15 fields)

These can be handled during migration or created later if needed:

### Can Skip Initially (Handle During Migration)
1. `project_name` - Char (can derive from project_id if exists)
2. `scope_of_work` - Text (can be migrated as-is)
3. `engineer_name` - Char (can be migrated as-is)
4. `effective_date` - Date (can be migrated as-is)
5. `safety_hse_quality` - Boolean (can be migrated as-is)
6. `is_warning` - Boolean (can be migrated as-is)
7. `is_tax_include` - Boolean (can be migrated as-is)
8. `is_reverse` - Boolean (can be migrated as-is)
9. `has_due` - Boolean (can be migrated as-is)
10. `require_payment` - Boolean (can be migrated as-is)
11. `show_update_pricelist` - Boolean (can be migrated as-is)
12. `quotation_reverse` - Boolean (can be migrated as-is)
13. `medium_id` - Many2one (can be migrated as-is)
14. `reference_drawing` - Char/Text (can be migrated as-is)
15. `signature` - Binary/Text (can be migrated as-is)

### Complex Fields (Handle During Migration)
16. `sale_order_option_ids` - One2many (needs related model setup)

---

## 📋 Migration Script Strategy

### Phase 1: Create Critical Fields First
```python
# Create these 5 fields before migration starts
CRITICAL_FIELDS = [
    'contract_id',
    'branch_id', 
    'source_id',
    'sale_oder_type',
    'currency_rate'
]
```

### Phase 2: Handle Field Mapping During Migration
```python
# Map renamed fields
FIELD_MAPPINGS = {
    'is_direct_order': 'direct_order',
    'is_lumpsum': 'lumpsum',
    'is_with_stamp': 'with_stamp',
    'is_with_unit_price': 'with_unit_price',
    'is_with_uom': 'with_uom',
    'is_brand': 'with_brand',
    'attention': 'attention_id',  # Char → Many2one (needs lookup)
    'client': 'client_id',  # Char → Many2one (needs lookup)
    'consultants': 'consultants_ids',  # Char → Many2many (needs lookup)
    'regards': 'thanks_and_regards',
}
```

### Phase 3: Create Missing Fields On-The-Fly During Migration
```python
# For each sale order being migrated:
# 1. Check if field exists
# 2. If not, create it dynamically OR skip if not critical
# 3. Map data from Odoo 14 to Odoo 19
```

---

## 🎯 Recommended Action Plan

### Step 1: Create Only Critical Fields (5 fields)
Create these 5 fields in `fm_amc_crm_custom/models/sale_order_extended.py`:
- contract_id
- branch_id
- source_id
- sale_oder_type
- currency_rate

### Step 2: Update Migration Script
- Handle field name mappings (9 renamed fields)
- Handle data type conversions (Char → Many2one)
- Skip non-critical fields OR create them dynamically during migration

### Step 3: Post-Migration Cleanup
- After migration, review which skipped fields are actually needed
- Create them only if data exists or functionality requires them

---

## 💡 Benefits of This Approach

1. **Faster Setup**: Only create what's truly needed
2. **Flexible**: Can add fields later based on actual usage
3. **Less Risk**: Fewer fields = fewer potential issues
4. **Migration-Friendly**: Handle field creation during migration when you have actual data

---

## ⚠️ Fields That Need Special Handling

### Char → Many2one Conversions
These need lookup logic during migration:
- `attention` → `attention_id` (find/create partner)
- `client` → `client_id` (find/create partner)
- `consultants` → `consultants_ids` (find/create partners)

### One2many Fields
- `sale_order_option_ids` - Needs related model setup first

---

## Summary

**Create NOW**: 5 critical fields
**Skip/Create During Migration**: 15+ fields
**Handle Mapping**: 9 renamed fields

This approach is **pragmatic and efficient** - create only what's essential, handle the rest during migration when you have actual data to work with.
