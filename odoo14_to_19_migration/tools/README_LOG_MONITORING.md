# Odoo Log Monitoring Script

Real-time log monitoring script for watching Odoo server logs during migration.

## File

`watch_odoo_logs.ps1` - PowerShell script for Windows

## Features

- Real-time log monitoring (tail-like functionality)
- Color-coded output based on log levels:
  - **Red**: Errors, Exceptions, Critical
  - **Yellow**: Warnings
  - **Green**: Info, Success messages
  - **Cyan**: Processing, Starting messages
  - **Gray**: Debug messages
- Automatic log file detection
- Filtering by pattern (default: vendor bill migration)
- Handles log file rotation
- Shows last 50 lines on startup

## Usage

### Basic Usage (Auto-detect log file):
```powershell
.\watch_odoo_logs.ps1
```

### Specify Log File Path:
```powershell
.\watch_odoo_logs.ps1 -LogPath "C:\odoo\logs\odoo.log"
```

### Filter by Pattern:
```powershell
.\watch_odoo_logs.ps1 -Filter "migration|invoice|vendor"
```

### Show Only Errors:
```powershell
.\watch_odoo_logs.ps1 -Errors
```

### Show All Logs (No Filtering):
```powershell
.\watch_odoo_logs.ps1 -All
```

## Parameters

- `-LogPath <path>` - Path to Odoo log file
  - If not specified, script will try to auto-detect common locations
- `-Filter <pattern>` - Regex pattern to filter log entries
  - Default: `"vendor.bill|vendor_bill|Vendor Bill|migration"`
- `-All` - Show all log entries (no filtering)
- `-Errors` - Show only errors and warnings
- `-Help` - Show help message

## Auto-Detection

The script automatically searches for log files in common locations:
- `C:\odoo\logs\odoo.log`
- `C:\odoo\odoo.log`
- `D:\odoo\logs\odoo.log`
- `E:\odoo\logs\odoo.log`
- Current directory and parent directories
- User profile directories

## Output Example

```
========================================
Odoo Real-Time Log Monitor
========================================

Log File: C:\odoo\logs\odoo.log
Filter: vendor.bill|vendor_bill|Vendor Bill|migration

Press Ctrl+C to stop monitoring

========================================

2024-01-15 10:30:15,123 INFO odoo14_to_19_migration: 🔄 Starting SYNCHRONOUS migration for vendor bill BILL001
2024-01-15 10:30:16,456 INFO odoo14_to_19_migration: ✅ Successfully migrated vendor bill BILL001
2024-01-15 10:30:18,789 ERROR odoo14_to_19_migration: ❌ Error migrating vendor bill BILL002: Partner not found

--- Starting real-time monitoring ---

2024-01-15 10:30:20,012 INFO odoo14_to_19_migration: 🔄 Starting SYNCHRONOUS migration for vendor bill BILL003
```

## Stopping the Script

Press `Ctrl+C` to stop monitoring.

## Troubleshooting

### Log File Not Found

If the script can't find the log file:

1. **Specify path manually**:
   ```powershell
   .\watch_odoo_logs.ps1 -LogPath "C:\full\path\to\odoo.log"
   ```

2. **Check Odoo configuration**:
   - Log file path is usually set in `odoo.conf`
   - Look for `logfile` parameter

3. **Common locations**:
   - Windows: `C:\odoo\logs\odoo.log` or `C:\Program Files\Odoo\logs\odoo.log`
   - Check Odoo installation directory

### No Output

If no log entries are shown:

1. **Check filter**: Try `-All` to see all logs
   ```powershell
   .\watch_odoo_logs.ps1 -All
   ```

2. **Verify log file is being written**: Check file modification time

3. **Check file permissions**: Ensure script has read access

### Performance

For large log files:
- Script shows last 50 lines on startup
- Only monitors new entries in real-time
- Handles log rotation automatically

## Related Scripts

- `migrate_vendor_bills_continuous.ps1` - Continuous migration processor
- `migrate_vendor_bills.py` - Python migration helper

## Tips

1. **Run in separate terminal**: Keep log monitoring open while running migration
2. **Use filters**: Filter by specific bill numbers or errors
3. **Combine with migration**: Run both scripts simultaneously for full visibility

## Example Workflow

```powershell
# Terminal 1: Start log monitoring
.\watch_odoo_logs.ps1 -Filter "vendor.bill|migration"

# Terminal 2: Start migration
.\migrate_vendor_bills_continuous.ps1
```

This gives you:
- Real-time migration progress (Terminal 2)
- Detailed log entries (Terminal 1)
- Error details immediately visible

