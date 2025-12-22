# Purchase Order Line Field Mapping: Odoo 14 → Odoo 19

## Standard Fields Mapping

| Odoo 14 Field | Odoo 19 Field | Type | Required | Notes |
|--------------|---------------|------|----------|-------|
| `product_id` | `product_id` | Many2one | ✅ Yes | Product |
| `name` | `name` | Text | ✅ Yes | Description/Product Description |
| `product_qty` | `product_qty` | Float | ✅ Yes | Quantity |
| `product_uom` | `product_uom_id` | Many2one | ✅ Yes | **CHANGED**: `product_uom` → `product_uom_id` |
| `price_unit` | `price_unit` | Float | ✅ Yes | Unit Price |
| `taxes_id` | `taxes_id` | Many2many | No | Taxes |
| `date_planned` | `date_planned` | Datetime | No | Expected Arrival Date |
| `sequence` | `sequence` | Integer | No | Line Sequence |
| `discount` | `discount` | Float | No | Discount (%) |
| `price_subtotal` | `price_subtotal` | Float (computed) | No | Subtotal (computed) |
| `price_total` | `price_total` | Float (computed) | No | Total (computed) |
| `price_tax` | `price_tax` | Float (computed) | No | Tax Amount (computed) |
| `account_analytic_id` | `account_analytic_id` | Many2one | No | Analytic Account (Odoo 14) |
| `analytic_distribution` | `analytic_distribution` | JSON | No | Analytic Distribution (Odoo 19) |
| `product_packaging_id` | `product_packaging_id` | Many2one | No | Product Packaging |
| `product_packaging_qty` | `product_packaging_qty` | Float | No | Packaging Quantity |

## Critical Field Name Changes

### ⚠️ UoM Field Name Change
- **Odoo 14**: `product_uom` (Many2one)
- **Odoo 19**: `product_uom_id` (Many2one)
- **Action**: Must map `product_uom` → `product_uom_id` when creating lines

### ⚠️ Analytic Account Field Change
- **Odoo 14**: `account_analytic_id` (Many2one)
- **Odoo 19**: `analytic_distribution` (JSON) - preferred, but `account_analytic_id` still exists for compatibility
- **Action**: Try to map to `analytic_distribution` if available, fallback to `account_analytic_id`

## Custom Fields Mapping

### From odx_purchase_customisation / metro_erp (Odoo 14)

| Odoo 14 Field | Odoo 19 Field | Type | Status | Notes |
|--------------|---------------|------|--------|-------|
| `brand_id` | `brand_id` | Many2one | ✅ Mapped | Product brand (from eq_fc_purchase_custom) |
| `project_id` | `project_id` | Many2one | ✅ Mapped | Project |
| `customer_id` | `customer_id` | Many2one | ✅ Mapped | Customer |
| `project_orderline_id` | ❌ Not in Odoo 19 | Many2one | ❌ Not mapped | Project orderline link |
| `branch_id` | ❌ Not in Odoo 19 | Many2one | ❌ Not mapped | Branch (related from order) |
| `product_brand_id` | `brand_id` | Many2one | ✅ Mapped | Alternative brand field name |

### From eq_fc_purchase_custom (Odoo 19)

| Odoo 14 Field | Odoo 19 Field | Type | Status | Notes |
|--------------|---------------|------|--------|-------|
| ❌ Not in Odoo 14 | `brand_variant_id` | Many2one | ✅ Mapped | Brand variant (if exists) |

## Field Mapping Logic

### Required Fields (Must be set)
1. **`order_id`** - Purchase Order ID (set automatically)
2. **`product_id`** - Product (required, create fallback if missing)
3. **`name`** - Description (required, use product name if missing)
4. **`product_qty`** - Quantity (required, default to 1.0)
5. **`product_uom_id`** - UoM (required, use product default or "Units")
6. **`price_unit`** - Unit Price (required, default to 0.0)

### Optional Fields (Set if available)
- `taxes_id` - Taxes
- `date_planned` - Expected Arrival
- `sequence` - Line Sequence
- `discount` - Discount %
- `brand_id` - Brand
- `brand_variant_id` - Brand Variant
- `project_id` - Project
- `customer_id` - Customer
- `analytic_distribution` / `account_analytic_id` - Analytic Account

## Migration Code Requirements

1. **Always use `product_uom_id`** (not `product_uom`) when creating lines in Odoo 19
2. **Map `product_uom` from Odoo 14** to `product_uom_id` in Odoo 19
3. **Ensure all required fields are set** before creating the line
4. **Handle missing products** by creating a fallback service product
5. **Handle missing UoM** by using product default or "Units"
6. **Map taxes correctly** using Many2many format: `[(6, 0, [tax_ids])]`

## Common Issues

### Issue 1: UoM Field Name
- **Problem**: Using `product_uom` instead of `product_uom_id`
- **Solution**: Always use `product_uom_id` in Odoo 19

### Issue 2: Missing Product
- **Problem**: Product from Odoo 14 doesn't exist in Odoo 19
- **Solution**: Create fallback service product with same name

### Issue 3: Missing UoM
- **Problem**: UoM from Odoo 14 doesn't exist in Odoo 19
- **Solution**: Use product's default UoM or search for "Units"

### Issue 4: Tax Mapping
- **Problem**: Tax IDs from Odoo 14 don't match Odoo 19
- **Solution**: Verify tax exists before mapping, skip if not found

