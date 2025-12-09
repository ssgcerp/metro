# Odoo 14 to Odoo 19 Invoice & Purchase Migration Module

This module allows you to migrate invoices and purchase invoices (vendor bills) from an Odoo 14 instance to Odoo 19 using XML-RPC API.

## Features

- **Connection Management**: Configure and test connection to Odoo 14 instance
- **Data Preview**: Preview the number of records available for migration
- **Selective Migration**: Choose which document types to migrate (invoices, purchase invoices)
- **Progress Tracking**: Real-time progress bar during migration
- **Error Handling**: Comprehensive error logging and reporting
- **Automatic Data Mapping**: Automatically creates partners, products, and other related records

## Installation

1. Copy the `odoo14_to_19_migration` folder to your Odoo 19 addons directory
2. Update the apps list in Odoo
3. Install the module from Apps menu

## Usage

### Step 1: Configure Connection

1. Go to **Accounting > Odoo 14 Migration > Migration Configuration**
2. Click **Create** to add a new configuration
3. Fill in the following fields:
   - **Odoo 14 URL**: Full URL of your Odoo 14 instance (e.g., `http://odoo14.example.com`)
   - **Database**: Database name in Odoo 14
   - **Username**: Username for API access
   - **Password**: Password for API access
4. Click **Test Connection** to verify the connection
5. Save the configuration

### Step 2: Start Migration

1. Go to **Accounting > Odoo 14 Migration > Start Migration**
2. Select the migration configuration
3. Choose which documents to migrate:
   - **Migrate Customer Invoices**: Migrate customer invoices (out_invoice)
   - **Migrate Vendor Bills**: Migrate vendor bills (in_invoice)
4. Click **Check Data** to preview the number of records
5. Click **Start Migration** to begin the migration process
6. Monitor the progress in the **Migration Status** tab
7. Review the migration results and error log

## What Gets Migrated

### Invoices (Customer Invoices)
- Invoice header information (date, due date, partner, journal, etc.)
- Invoice line items with products, quantities, prices, and taxes
- Related partners (customers)
- Related products
- Tax information

### Purchase Invoices (Vendor Bills)
- Bill header information
- Bill line items with products, quantities, prices, and taxes
- Related partners (suppliers)
- Related products
- Tax information

## Data Mapping

The module automatically handles:
- **Partners**: Creates new partners if they don't exist, matches by name or VAT
- **Products**: Creates new products if they don't exist, matches by default_code or barcode
- **Accounts**: Uses existing accounts or defaults from journal/product category
- **Taxes**: Maps taxes by ID (requires taxes to exist in Odoo 19)
- **Journals**: Uses existing journals or defaults

## Important Notes

1. **Invoices are imported as Draft**: All migrated invoices are created in draft state for review
2. **Tax Mapping**: Ensure that tax IDs match between Odoo 14 and Odoo 19, or taxes may not be applied correctly
3. **Journal Mapping**: Ensure journals exist in Odoo 19 with matching IDs or the system will use defaults
4. **Large Datasets**: For large datasets, the migration may take time. Monitor the progress bar
5. **Error Handling**: Review the error log after migration to identify any issues

## Technical Details

- Uses XML-RPC API for Odoo 14 connection
- Compatible with Odoo 19 Enterprise
- Follows Odoo development best practices
- Includes comprehensive error logging

## Troubleshooting

### Connection Issues
- Verify the Odoo 14 URL is accessible
- Check that XML-RPC is enabled in Odoo 14
- Verify database name, username, and password are correct
- Ensure the user has appropriate permissions in Odoo 14

### Migration Errors
- Check the error log in the Migration Status tab
- Verify that required data (partners, products, accounts) exists or can be created
- Ensure journal IDs match between systems or use default journals
- Review Odoo logs for detailed error messages

## Support

For issues or questions, please contact your system administrator or refer to Odoo documentation.

