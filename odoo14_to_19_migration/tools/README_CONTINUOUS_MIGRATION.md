# Continuous Vendor Bill Migration Script

This script provides continuous processing of vendor bill migrations from Odoo 14 to Odoo 19.

## Files

- `migrate_vendor_bills_continuous.sh` - Bash script for Linux/Unix systems
- `migrate_vendor_bills_continuous.ps1` - PowerShell script for Windows systems

## Features

- Processes vendor bills one by one from the queue
- Shows real-time progress with colored output
- Displays: Bill Number | Total Queued | Migrated | Current Migration | Status
- Automatically stops when queue is empty
- Handles stuck migrations (resets after 30 seconds)
- Tracks processed bills to avoid duplicates

## Prerequisites

1. **Odoo Server Running**: Odoo 19 instance must be running
2. **Database Access**: Database must be accessible via HTTP
3. **Module Installed**: `odoo14_to_19_migration` module must be installed and upgraded
4. **Vendor Bills Queued**: Bills must be in "queued" status
5. **Optional**: `jq` for better JSON parsing (install with: `sudo apt-get install jq`)

## Configuration

Edit the script to set your configuration:

```bash
ODOO_URL="http://localhost:8079"      # Your Odoo URL
DATABASE="metrodb"                    # Your database name
PROCESSING_DELAY=2                    # Seconds between processing each bill
```

## Usage

### Linux/Unix (Bash Script)

#### 1. Make script executable:
```bash
chmod +x migrate_vendor_bills_continuous.sh
```

#### 2. Run the script:
```bash
./migrate_vendor_bills_continuous.sh
```

### Windows (PowerShell Script)

#### 1. Run PowerShell as Administrator (if needed):
```powershell
# Right-click PowerShell and select "Run as Administrator"
```

#### 2. Run the script:
```powershell
.\migrate_vendor_bills_continuous.ps1
```

#### 3. If execution policy blocks the script:
```powershell
# Allow script execution for current session
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# Then run the script
.\migrate_vendor_bills_continuous.ps1
```

### The script will:
- Establish database session
- Check initial status
- Process bills one by one
- Display progress in real-time
- Stop when queue is empty

## Output Format

```
Bill | Total Queued | Migrated | Current Migration | Status
BILL001 | Total Queued: 50 | Migrated: 10 | Current: BILL001 - DONE | Status: ✅ DONE
BILL002 | Total Queued: 49 | Migrated: 11 | Current: BILL002 - in progress | Status: 🔄 In Progress
BILL003 | Total Queued: 48 | Migrated: 12 | Current: BILL003 - ERROR: ... | Status: ❌ ERROR
```

## Status Colors

- **Green** ✅ - Successfully migrated
- **Yellow** 🔄 - Currently migrating
- **Red** ❌ - Error occurred

## Stopping the Script

Press `Ctrl+C` to stop the script at any time. The script will stop gracefully.

## Troubleshooting

### Route Not Found (404)
```
❌ Route not found (404)
   Please upgrade the module: Apps > odoo14_to_19_migration > Upgrade
   Then FULLY restart Odoo server
```

**Solution**: Upgrade the module and restart Odoo server completely.

### Database Not Found
```
❌ Failed to establish session (HTTP XXX)
   Please ensure Odoo is running and database 'xxx' exists
```

**Solution**: 
- Check Odoo is running
- Verify database name is correct
- Check database exists

### No Bills in Queue
```
✅ No vendor bills in queue. Nothing to process.
```

**Solution**: 
- Upload vendor bills via Excel
- Queue bills for migration in Odoo UI
- Check bills are in "queued" status

### Stuck Migrations

The script automatically detects and resets stuck migrations (bills stuck in "migrating" status for more than 30 seconds).

## API Endpoints Used

The script uses these HTTP endpoints:

1. **Status Endpoint**: `/migration/status_vendor_bill?db=DATABASE`
   - Returns JSON with migration status
   - Fields: `total_queued`, `migrating_now`, `total_migrated`, `total_errors`

2. **Process Endpoint**: `/migration/process_one_vendor_bill?db=DATABASE`
   - Processes one vendor bill from queue
   - Returns text response with current status

## Workflow

1. **Upload Excel**: Upload vendor bill numbers via Odoo UI
   - Go to: Odoo 14 Migration → Vendors → Vendor Bills → Upload Excel

2. **Queue Bills**: Mark bills as "queued" for migration
   - Select bills with "Pending Migration" status
   - Click "Migrate Selected" to queue them

3. **Run Script**: Start continuous migration
   ```bash
   ./migrate_vendor_bills_continuous.sh
   ```

4. **Monitor Progress**: Watch real-time progress in terminal

5. **Check Results**: Review migrated bills in Odoo UI
   - Go to: Odoo 14 Migration → Vendors → Vendor Bills
   - Filter by status: "Migrated" or "Error"

## Example Session

```bash
$ ./migrate_vendor_bills_continuous.sh

=== Vendor Bill Migration Processor ===

Configuration:
  Database: metrodb
  URL: http://localhost:8079
  Processing Delay: 2 seconds

Establishing database session...
  ✅ Session established

  ✅ Initial status retrieved

Starting migration process...
Press Ctrl+C to stop at any time

========================================
Bill | Total Queued | Migrated | Current Migration | Status
========================================

BILL001 | Total Queued: 50 | Migrated: 0 | Current: BILL001 - DONE | Status: ✅ DONE
BILL002 | Total Queued: 49 | Migrated: 1 | Current: BILL002 - DONE | Status: ✅ DONE
BILL003 | Total Queued: 48 | Migrated: 2 | Current: BILL003 - DONE | Status: ✅ DONE
...

========================================
   ✅ Migration Complete!
========================================

Final Summary:
  Total Migrated: 50
  Total Errors: 0
```

## Related Scripts

- `migrate_vendor_bills.py` - Python script for checking status and managing migration
- `migrate_vendor_bills.ps1` - PowerShell script for Windows (helper script)
- `migrate_vendor_bills.bat` - Batch script for Windows
- `migrate_vendor_bills_continuous.ps1` - PowerShell script for continuous migration (Windows)
- `migrate_vendor_bills_continuous.sh` - Bash script for continuous migration (Linux/Unix)

## Support

For issues:
1. Check Odoo server logs
2. Review migration logs: `logs/failed_vendor_bill_migrations.log`
3. Check bills status in Odoo UI
4. Verify module is upgraded and server restarted

