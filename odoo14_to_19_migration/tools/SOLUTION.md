# ✅ SOLUTION: Route Works in Browser, Not PowerShell

## The Problem
- Route works in browser: `http://localhost:8079/migration/test` ✅
- Route returns 404 from PowerShell: `404 - No database is selected` ❌

## Root Cause
Odoo 19 requires database selection BEFORE routing to controllers, even with `auth='none'`. The `?db=metrodb` query parameter is not being parsed early enough in Odoo's request handling.

## ✅ WORKING SOLUTION: Use Browser Session

Since the route works in the browser, you have two options:

### Option 1: Use Browser URL Directly (Simplest)
Just use the browser URL in your scripts. If you need automation, use a tool that can maintain a browser session.

### Option 2: Access Through Web Interface First
Create a session by accessing the web interface, then use that session:

```powershell
# Get a web session first
$session = Invoke-WebRequest -Uri "http://localhost:8079/web?db=metrodb" -SessionVariable webSession -UseBasicParsing

# Then use the session for the migration route
$response = Invoke-WebRequest -Uri "http://localhost:8079/migration/process_one?db=metrodb" -WebSession $webSession -UseBasicParsing
```

### Option 3: Use XML-RPC Instead
Instead of HTTP routes, use Odoo's XML-RPC API which handles database selection properly:

```powershell
# This would require creating an XML-RPC method instead of HTTP route
```

## 🎯 RECOMMENDED: Update Your Scripts

Update `migrate_one.ps1` to use a web session:

```powershell
$ODOO_URL = "http://localhost:8079"
$DATABASE = "metrodb"

# Get web session first
try {
    $null = Invoke-WebRequest -Uri "$ODOO_URL/web?db=$DATABASE" -SessionVariable webSession -UseBasicParsing -ErrorAction Stop
    
    # Now call migration route with session
    $response = Invoke-WebRequest -Uri "$ODOO_URL/migration/process_one?db=$DATABASE" -WebSession $webSession -UseBasicParsing
    Write-Host $response.Content
} catch {
    Write-Host "ERROR: $_"
    exit 1
}
```

## Why This Works
- Browser: Already has database session → Route works ✅
- PowerShell without session: No database selected → 404 ❌
- PowerShell with web session: Database selected via web interface → Route works ✅

