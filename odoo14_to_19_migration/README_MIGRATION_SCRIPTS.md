# Vendor Bill Migration Scripts

This directory contains helper scripts for vendor bill migration from Odoo 14 to Odoo 19.

## Available Scripts

### 1. Python Script (Recommended)
**File**: `migrate_vendor_bills.py`

Most comprehensive script with direct database access.

**Usage**:
```bash
# Check installation and modules
python migrate_vendor_bills.py --check -d odoo19

# View migration status
python migrate_vendor_bills.py --status -d odoo19

# Upgrade module
python migrate_vendor_bills.py --upgrade -d odoo19

# Test Odoo 14 connection
python migrate_vendor_bills.py --test-connection -d odoo19

# View migration logs
python migrate_vendor_bills.py --logs

# Run all checks
python migrate_vendor_bills.py --all -d odoo19
```

**Requirements**:
- Python 3.x
- Odoo installed and accessible
- Run from Odoo environment or with proper PYTHONPATH

### 2. PowerShell Script (Windows)
**File**: `migrate_vendor_bills.ps1`

Windows PowerShell script for quick checks.

**Usage**:
```powershell
# Check installation
.\migrate_vendor_bills.ps1 -Check

# View status
.\migrate_vendor_bills.ps1 -Status

# Upgrade module
.\migrate_vendor_bills.ps1 -Upgrade

# View logs
.\migrate_vendor_bills.ps1 -Logs

# Run all checks
.\migrate_vendor_bills.ps1 -All
```

**Parameters**:
- `-Database <name>` - Database name (default: odoo19)
- `-OdooBin <path>` - Path to odoo-bin (default: odoo-bin)
- `-Check` - Check installation and modules
- `-Status` - View migration status
- `-Upgrade` - Upgrade migration module
- `-TestConnection` - Test Odoo 14 connection
- `-Logs` - View migration logs
- `-All` - Run all checks
- `-Help` - Show help message

### 3. Batch Script (Windows)
**File**: `migrate_vendor_bills.bat`

Simple Windows batch file for basic operations.

**Usage**:
```cmd
migrate_vendor_bills.bat --check
migrate_vendor_bills.bat --status
migrate_vendor_bills.bat --upgrade
migrate_vendor_bills.bat --logs
migrate_vendor_bills.bat --all
```

### 4. Shell Script (Linux/Mac)
**File**: `migrate_vendor_bills.sh`

Bash script for Linux/Mac systems.

**Usage**:
```bash
chmod +x migrate_vendor_bills.sh
./migrate_vendor_bills.sh --check
./migrate_vendor_bills.sh --status
./migrate_vendor_bills.sh --upgrade
./migrate_vendor_bills.sh --logs
./migrate_vendor_bills.sh --all
```

## Quick Start Guide

### 1. Check Installation
```bash
python migrate_vendor_bills.py --check -d odoo19
```

This will verify:
- Required modules are installed
- Migration configurations exist
- Odoo connection is working

### 2. View Migration Status
```bash
python migrate_vendor_bills.py --status -d odoo19
```

This shows:
- Number of bills by status (pending, queued, migrating, migrated, error)
- Recent errors
- Total bills in migration queue

### 3. Upgrade Module
```bash
python migrate_vendor_bills.py --upgrade -d odoo19
```

Upgrades the `odoo14_to_19_migration` module to latest version.

### 4. Test Odoo 14 Connection
```bash
python migrate_vendor_bills.py --test-connection -d odoo19
```

Tests XML-RPC connection to Odoo 14 instance.

### 5. View Logs
```bash
python migrate_vendor_bills.py --logs
```

Shows failed migration entries from log file.

## Migration Workflow

1. **Upload Excel**: Upload vendor bill numbers via Odoo UI
   - Go to: Odoo 14 Migration → Vendors → Vendor Bills → Upload Excel

2. **Check Status**: Verify bills are ready for migration
   ```bash
   python migrate_vendor_bills.py --status -d odoo19
   ```

3. **Start Migration**: Use Odoo UI to queue and start migration
   - Select bills with "Pending Migration" status
   - Click "Migrate Selected" to queue them
   - Click "Start Queued Migration" to begin processing

4. **Monitor Progress**: Check status regularly
   ```bash
   python migrate_vendor_bills.py --status -d odoo19
   ```

5. **View Errors**: Check logs for any failures
   ```bash
   python migrate_vendor_bills.py --logs
   ```

## Troubleshooting

### Module Not Found
If modules are not found, install them:
- Go to: Apps → Search for module → Install

### Connection Failed
Check migration configuration:
- Go to: Odoo 14 Migration → Migration Configuration
- Verify URL, database, username, and password
- Click "Test Connection"

### Migration Stuck
If migration is stuck:
1. Check queue jobs: Go to: Settings → Technical → Queue Jobs
2. Restart Odoo server
3. Check logs: `python migrate_vendor_bills.py --logs`

### Bills Not Migrating
1. Check status: `python migrate_vendor_bills.py --status -d odoo19`
2. Verify bills exist in Odoo 14
3. Check error messages in migration line records
4. Review log file for details

## Environment Variables

For Python script:
- `ODOO_BIN` - Path to odoo-bin (default: odoo-bin)
- `ODOO_CONFIG` - Path to Odoo config file
- `DATABASE` - Database name (default: odoo19)

## Support

For issues or questions:
1. Check migration logs
2. Review error messages in Odoo UI
3. Check Odoo server logs
4. Contact development team

