# Migration Code Updates - Sale Order Field Mapping

## Summary
Updated the `customer_migration_wizard.py` to implement the field mapping strategy we discussed:
- **Skip non-critical fields** during migration
- **Map renamed fields** (9 fields)
- **Handle Char → Many2one conversions** (attention, client, consultants)
- **Migrate 5 critical fields** (contract_id, branch_id, source_id, sale_oder_type, currency_rate)

---

## Changes Made

### 1. Added Field Mapping Dictionary
```python
FIELD_MAPPINGS = {
    'is_direct_order': 'direct_order',
    'is_lumpsum': 'lumpsum',
    'is_with_stamp': 'with_stamp',
    'is_with_unit_price': 'with_unit_price',
    'is_with_uom': 'with_uom',
    'is_brand': 'with_brand',
    'attention': 'attention_id',  # Char → Many2one
    'client': 'client_id',  # Char → Many2one
    'consultants': 'consultants_ids',  # Char → Many2many
    'regards': 'thanks_and_regards',
}
```

### 2. Added Skip Fields List
Fields that are skipped (non-critical, can be handled later):
```python
SKIP_FIELDS = [
    'project_name', 'scope_of_work', 'engineer_name', 'effective_date',
    'safety_hse_quality', 'is_warning', 'is_tax_include', 'is_reverse',
    'has_due', 'require_payment', 'show_update_pricelist', 'quotation_reverse',
    'medium_id', 'reference_drawing', 'signature', 'sale_order_option_ids',
    'date_start', 'lock_sale',
]
```

### 3. Added Critical Fields List
Fields that should be migrated (5 critical fields):
```python
CRITICAL_FIELDS = [
    'contract_id', 'branch_id', 'source_id', 
    'sale_oder_type', 'currency_rate'
]
```

### 4. Added Helper Methods

#### `_find_or_create_contact_partner(contact_name, parent_partner, contact_type)`
- Finds or creates a contact partner (child of parent_partner)
- Used for `attention` → `attention_id` conversion

#### `_find_or_create_partner_by_name(partner_name)`
- Finds or creates a partner by name
- Used for `client` → `client_id` and `consultants` → `consultants_ids` conversions

### 5. Updated `_prepare_quotation_vals` Method

**Before processing custom fields:**
1. Apply field name mappings (Odoo 14 → Odoo 19)
2. Skip non-critical fields
3. Handle Char → Many2one conversions:
   - `attention` → `attention_id` (find/create contact partner)
   - `client` → `client_id` (find/create partner)
   - `consultants` → `consultants_ids` (find/create multiple partners)

**During custom field processing:**
- Log critical fields migration
- Warn if critical fields don't exist in Odoo 19
- Skip fields that don't exist (non-critical)

---

## Migration Flow

```
1. Get quotation data from Odoo 14
   ↓
2. Apply field name mappings (9 fields)
   ↓
3. Handle Char → Many2one conversions (3 fields)
   ↓
4. Skip non-critical fields (15+ fields)
   ↓
5. Process remaining custom fields
   - Check if field exists in Odoo 19
   - Log critical fields
   - Warn if critical fields missing
   - Skip if field doesn't exist (non-critical)
   ↓
6. Create quotation in Odoo 19
```

---

## Field Mapping Examples

### Example 1: Direct Mapping
```python
# Odoo 14: is_direct_order = True
# Odoo 19: direct_order = True
```

### Example 2: Char → Many2one
```python
# Odoo 14: attention = "Mr. John Doe"
# Odoo 19: attention_id = <partner_id> (finds or creates contact partner)
```

### Example 3: Char → Many2many
```python
# Odoo 14: consultants = "Consultant A, Consultant B"
# Odoo 19: consultants_ids = [(6, 0, [partner_id_1, partner_id_2])]
```

---

## Logging

The migration now includes detailed logging:
- ✅ **INFO**: Field mappings applied
- ✅ **INFO**: Critical fields migrated
- ⚠️ **WARNING**: Critical fields missing in Odoo 19
- 🔍 **DEBUG**: Non-critical fields skipped

---

## Next Steps

1. **Create 5 critical fields** in `fm_amc_crm_custom/models/sale_order_extended.py`:
   - contract_id
   - branch_id
   - source_id
   - sale_oder_type
   - currency_rate

2. **Test migration** with sample quotations

3. **Review logs** to see which fields were migrated/skipped

4. **Post-migration**: Add skipped fields only if needed based on actual data

---

## Notes

- Non-critical fields are **skipped silently** (logged at DEBUG level)
- Critical fields will **warn** if they don't exist in Odoo 19
- Char → Many2one conversions **create partners** if they don't exist
- Field mappings are applied **before** custom field processing
