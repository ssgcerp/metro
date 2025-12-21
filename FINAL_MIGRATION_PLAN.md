# Final Migration Plan: Field Creation Strategy

## ✅ Decision: Skip Non-Critical Fields, Handle During Migration

**Strategy**: Only create **5 critical fields** now. Handle the rest during migration when we have actual data.

---

## 🎯 Fields to Create NOW (5 fields)

Add these to `fm_amc_crm_custom/models/sale_order_extended.py`:

```python
# Critical Business Fields
contract_id = fields.Many2one('amc.contract', string='AMC Contract', 
                              tracking=True, help='Linked AMC Contract')
branch_id = fields.Many2one('res.company', string='Branch', 
                            default=lambda self: self.env.company, 
                            tracking=True, help='Branch/Company')
source_id = fields.Many2one('utm.source', string='Source', 
                           tracking=True, help='Lead source')
sale_oder_type = fields.Selection([
    ('amc', 'AMC'),
    ('project', 'Project'),
    ('direct', 'Direct'),
    ('other', 'Other')
], string='Order Type', tracking=True, help='Type of sale order')
currency_rate = fields.Float(string='Currency Rate', digits=(12, 6),
                             help='Currency conversion rate')
```

---

## ⏸️ Fields to Skip (Handle During Migration)

**15+ fields** can be skipped and handled during migration:
- Simple fields: `project_name`, `scope_of_work`, `engineer_name`, `effective_date`
- Boolean flags: `safety_hse_quality`, `is_warning`, `is_tax_include`, `is_reverse`, `has_due`, `require_payment`, `show_update_pricelist`, `quotation_reverse`
- Reference fields: `medium_id`, `reference_drawing`
- Complex: `sale_order_option_ids` (One2many), `signature` (Binary)

**Migration Script Logic:**
```python
# During migration:
# 1. If field exists in Odoo 19 → map data
# 2. If field doesn't exist → skip OR create dynamically if critical
# 3. Handle field name mappings (9 renamed fields)
```

---

## 📋 Field Name Mappings (9 fields)

Migration script must handle these mappings:

| Odoo 14 | Odoo 19 | Action |
|---------|---------|--------|
| `is_direct_order` | `direct_order` | Direct mapping |
| `is_lumpsum` | `lumpsum` | Direct mapping |
| `is_with_stamp` | `with_stamp` | Direct mapping |
| `is_with_unit_price` | `with_unit_price` | Direct mapping |
| `is_with_uom` | `with_uom` | Direct mapping |
| `is_brand` | `with_brand` | Direct mapping |
| `attention` | `attention_id` | **Lookup**: Find/create partner |
| `client` | `client_id` | **Lookup**: Find/create partner |
| `consultants` | `consultants_ids` | **Lookup**: Find/create partners |
| `regards` | `thanks_and_regards` | Direct mapping |

---

## ✅ Confirmed Models

- ✅ `contract_id` → `amc.contract` (exists in amc_contracts module)
- ✅ `branch_id` → `res.company` (standard Odoo, same as amc_contract uses)
- ✅ `source_id` → `utm.source` (standard Odoo UTM module)

---

## 📝 Next Steps

1. **Add 5 critical fields** to `sale_order_extended.py`
2. **Update migration script** with:
   - Field name mappings
   - Char → Many2one lookup logic (attention, client, consultants)
   - Skip logic for non-critical fields
3. **Test migration** with sample data
4. **Post-migration**: Review and add skipped fields only if needed

---

## 💡 Benefits

✅ **Faster setup** - Only 5 fields to create now  
✅ **Flexible** - Can add fields during/after migration  
✅ **Less risk** - Fewer fields = fewer potential issues  
✅ **Data-driven** - Create fields based on actual migrated data  

---

## Summary

**Create NOW**: 5 critical fields  
**Skip**: 15+ fields (handle during migration)  
**Map**: 9 renamed fields  
**Total effort**: Minimal upfront, handle rest during migration ✅
