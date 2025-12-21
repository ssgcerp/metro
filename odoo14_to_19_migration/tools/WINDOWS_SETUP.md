# Windows Batch Files for Migration

Simple batch files to run migration from Windows command line or Task Scheduler.

## Available Batch Files

### 1. `migrate_one.bat`
**Simple one-time execution**
- Processes one quotation
- Shows output in console
- No logging

**Usage:**
```batch
migrate_one.bat
```

### 2. `migrate_one_with_logging.bat` (Command Prompt) or `migrate_one_with_logging.ps1` (PowerShell)
**One-time execution with logging**
- Processes one quotation
- Logs output to `C:\logs\migration.log`
- Includes timestamps

**Usage (Command Prompt):**
```batch
migrate_one_with_logging.bat
```

**Usage (PowerShell):**
```powershell
.\migrate_one_with_logging.ps1
```

### 3. `check_status.bat` (Command Prompt) or `check_status.ps1` (PowerShell)
**Check status only (no processing)**
- Shows current migration status
- Returns JSON format (pretty-printed in PowerShell)
- Does NOT process any quotations

**Usage (Command Prompt):**
```batch
check_status.bat
```

**Usage (PowerShell):**
```powershell
.\check_status.ps1
```

### 4. `migrate_continuous.bat`
**Continuous processing**
- Processes quotations continuously
- Runs every 60 seconds (configurable)
- Logs all output
- Press Ctrl+C to stop

**Usage:**
```batch
migrate_continuous.bat
```

## Configuration

Edit the batch files to change:
- `ODOO_URL`: Your Odoo URL (default: `http://localhost:8079`)
- `ENDPOINT`: Migration endpoint (default: `/migration/process_one`)
- `LOG_FILE`: Log file path (default: `C:\logs\migration.log`)
- `DELAY_SECONDS`: Delay between calls in continuous mode (default: 60)

## Setup Windows Task Scheduler

### Method 1: Using GUI

1. **Open Task Scheduler**
   - Press `Win + R`, type `taskschd.msc`, press Enter

2. **Create Basic Task**
   - Click "Create Basic Task" in right panel
   - Name: "Migration Process One"
   - Description: "Process one quotation every minute"

3. **Set Trigger**
   - Trigger: Daily (or as needed)
   - Start: Current date/time
   - Recur every: 1 minute

4. **Set Action**
   - **Option A (Batch file):** Action: Start a program → Browse to `migrate_one_with_logging.bat`
   - **Option B (PowerShell):** Action: Start a program → Program: `powershell.exe` → Arguments: `-ExecutionPolicy Bypass -File "E:\odoo modules\19\metro\odoo14_to_19_migration\tools\migrate_one_with_logging.ps1"`
   - Start in: `E:\odoo modules\19\metro\odoo14_to_19_migration\tools`

5. **Finish**
   - Check "Open the Properties dialog"
   - Click Finish
   - In Properties:
     - Check "Run whether user is logged on or not"
     - Check "Run with highest privileges" (if needed)

### Method 2: Using Command Line

**For Batch File:**
```batch
schtasks /create /tn "Migration Process One" /tr "E:\odoo modules\19\metro\odoo14_to_19_migration\tools\migrate_one_with_logging.bat" /sc minute /mo 1 /ru SYSTEM
```

**For PowerShell Script:**
```batch
schtasks /create /tn "Migration Process One" /tr "powershell.exe -ExecutionPolicy Bypass -File \"E:\odoo modules\19\metro\odoo14_to_19_migration\tools\migrate_one_with_logging.ps1\"" /sc minute /mo 1 /ru SYSTEM
```

**Parameters:**
- `/tn`: Task name
- `/tr`: Task to run (full path to batch file)
- `/sc`: Schedule type (minute, hourly, daily, etc.)
- `/mo`: Modifier (1 = every 1 minute)
- `/ru`: Run as user (SYSTEM = run as system service)

### View/Edit Scheduled Task

```batch
REM View task
schtasks /query /tn "Migration Process One"

REM Edit task
schtasks /change /tn "Migration Process One" /tr "new_path\file.bat"

REM Delete task
schtasks /delete /tn "Migration Process One" /f
```

## Requirements

### curl Command
The batch files use `curl` which is available in:
- Windows 10 (version 1803+) - Built-in
- Windows 11 - Built-in
- Older Windows - Download from: https://curl.se/windows/

**Check if curl is available:**
```batch
curl --version
```

**If curl is not available, use PowerShell instead:**

Create `migrate_one.ps1`:
```powershell
$url = "http://localhost:8079/migration/process_one"
Invoke-WebRequest -Uri $url -UseBasicParsing | Select-Object -ExpandProperty Content
```

## Testing

### Test the URL directly:
```batch
curl http://localhost:8079/migration/process_one
```

### Test status endpoint:
```batch
curl http://localhost:8079/migration/status
```

### Test batch file (Command Prompt):
```batch
cd "E:\odoo modules\19\metro\odoo14_to_19_migration\tools"
migrate_one.bat
```

### Test batch file (PowerShell):
```powershell
cd "E:\odoo modules\19\metro\odoo14_to_19_migration\tools"
.\migrate_one.bat
```

**Note:** In PowerShell, you need `.\` prefix to run files in current directory.

### Test PowerShell script:
```powershell
cd "E:\odoo modules\19\metro\odoo14_to_19_migration\tools"
.\migrate_one.ps1
```

If you get execution policy error, run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Expected Output

### migrate_one.bat output:
```
Total Queued: 1000
Migrating Now: S00061
DONE
```

### check_status.bat output:
```json
{
  "total_queued": 1000,
  "migrating_now": "S00061",
  "total_migrated": 50,
  "total_errors": 2
}
```

## Troubleshooting

### curl not found
- Install curl or use PowerShell version
- Or use `wget` if available

### Permission denied
- Run batch file as Administrator
- Or configure Task Scheduler to run with appropriate permissions

### URL not accessible
- Check Odoo is running
- Verify URL and port are correct
- Check firewall settings

### No output
- Check log file (if using logging version)
- Run with `@echo on` to see commands
- Test URL directly in browser

## PowerShell Scripts Available

PowerShell versions are included:
- `migrate_one.ps1` - Simple execution
- `migrate_one_with_logging.ps1` - With logging
- `check_status.ps1` - Status check with pretty JSON

**PowerShell Execution Policy:**
If you get execution policy error, run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Run PowerShell script:**
```powershell
.\migrate_one.ps1
```

**Schedule PowerShell script in Task Scheduler:**
- Program: `powershell.exe`
- Arguments: `-ExecutionPolicy Bypass -File "E:\odoo modules\19\metro\odoo14_to_19_migration\tools\migrate_one_with_logging.ps1"`
