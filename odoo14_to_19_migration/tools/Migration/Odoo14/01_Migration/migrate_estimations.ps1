# PowerShell script for Estimation Migration
# Triggers queue job runner to process estimation migration queue jobs
#
# Prerequisites:
# 1. Upload Excel file in Odoo UI (Odoo 14 Migration > Estimation > Upload Excel)
# 2. Select estimations and click "Migrate Selected" in Odoo UI
# 3. Queue jobs are created and pending
# 4. Run this script to trigger the queue job runner
#
# Note: Queue jobs are processed automatically by queue_job_cron_jobrunner module,
# but you can also trigger them manually using this script or the "Process Queue Jobs Now" button in Odoo UI

# Configuration - Change these if needed
$ODOO_URL = "http://localhost:8079"
$DATABASE = "metrodb"  # Change this to your database name
$USERNAME = "admin"    # Change to your Odoo username
$PASSWORD = "Amaze@321"    # Change to your Odoo password

function Invoke-OdooXMLRPC {
    param(
        [string]$Url,
        [string]$XmlBody
    )
    
    try {
        # Use UTF8 encoding for the XML body
        $utf8Bytes = [System.Text.Encoding]::UTF8.GetBytes($XmlBody)
        $response = Invoke-WebRequest -Uri $Url -Method Post -Body $utf8Bytes -ContentType "text/xml; charset=utf-8" -UseBasicParsing -ErrorAction Stop
        return $response.Content
    } catch {
        $errorDetails = $_.Exception.Message
        if ($_.Exception.Response) {
            $statusCode = $_.Exception.Response.StatusCode.value__
            $statusDescription = $_.Exception.Response.StatusDescription
            try {
                $stream = $_.Exception.Response.GetResponseStream()
                $reader = New-Object System.IO.StreamReader($stream)
                $responseBody = $reader.ReadToEnd()
                $errorDetails = "HTTP $statusCode $statusDescription`: $responseBody"
            } catch {
                $errorDetails = "HTTP $statusCode $statusDescription`: $errorDetails"
            }
        }
        throw "XML-RPC Error: $errorDetails"
    }
}

try {
    Write-Host ""
    Write-Host "=== Estimation Migration Queue Processor ===" -ForegroundColor Cyan
    Write-Host ""
    
    # Authenticate with Odoo using XML-RPC
    Write-Host "Authenticating with Odoo..." -ForegroundColor Yellow
    Write-Host "  Database: $DATABASE" -ForegroundColor Gray
    Write-Host "  Username: $USERNAME" -ForegroundColor Gray
    Write-Host "  URL: $ODOO_URL/xmlrpc/2/common" -ForegroundColor Gray
    
    $commonUrl = "$ODOO_URL/xmlrpc/2/common"
    
    # Test if Odoo server is accessible
    try {
        $testResponse = Invoke-WebRequest -Uri "$ODOO_URL/web" -Method Get -UseBasicParsing -ErrorAction Stop -TimeoutSec 5
        Write-Host "  ✅ Odoo server is accessible" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠️  Cannot access Odoo server at $ODOO_URL" -ForegroundColor Yellow
        Write-Host "     Please ensure Odoo is running" -ForegroundColor Gray
    }
    
    # Test if XML-RPC endpoint is available
    Write-Host "Testing XML-RPC endpoint..." -ForegroundColor Yellow
    try {
        $testXmlRpc = Invoke-WebRequest -Uri $commonUrl -Method Post -Body "<?xml version='1.0'?><methodCall><methodName>version</methodName><params></params></methodCall>" -ContentType "text/xml; charset=utf-8" -UseBasicParsing -ErrorAction Stop -TimeoutSec 5
        Write-Host "  ✅ XML-RPC endpoint is accessible" -ForegroundColor Green
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode -eq 404) {
            Write-Host "  ❌ XML-RPC endpoint returned 404 (Not Found)" -ForegroundColor Red
            Write-Host "" -ForegroundColor Red
            Write-Host "XML-RPC might be disabled in Odoo 19." -ForegroundColor Yellow
            Write-Host "" -ForegroundColor Yellow
            Write-Host "To enable XML-RPC in Odoo 19:" -ForegroundColor Yellow
            Write-Host "  1. Edit your Odoo configuration file (odoo.conf)" -ForegroundColor Gray
            Write-Host "  2. Add or uncomment: xmlrpc = True" -ForegroundColor Gray
            Write-Host "  3. Restart Odoo server" -ForegroundColor Gray
            Write-Host "" -ForegroundColor Gray
            Write-Host "Alternative: Use the Odoo UI instead:" -ForegroundColor Yellow
            Write-Host "  1. Go to: $ODOO_URL/web" -ForegroundColor Gray
            Write-Host "  2. Navigate to: Odoo 14 Migration > Estimation" -ForegroundColor Gray
            Write-Host "  3. Click 'Process Queue Jobs Now' from the Action menu" -ForegroundColor Gray
            Write-Host "" -ForegroundColor Gray
        } else {
            Write-Host "  ⚠️  XML-RPC test failed: HTTP $statusCode" -ForegroundColor Yellow
        }
    }
    
    $authXml = @"
<?xml version='1.0' encoding='UTF-8'?>
<methodCall>
  <methodName>authenticate</methodName>
  <params>
    <param><value><string>$DATABASE</string></value></param>
    <param><value><string>$USERNAME</string></value></param>
    <param><value><string>$PASSWORD</string></value></param>
    <param><value><struct></struct></value></param>
  </params>
</methodCall>
"@
    
    try {
        $authResponse = Invoke-OdooXMLRPC -Url $commonUrl -XmlBody $authXml
        $uid = 0
        
        # Try to parse the response
        if ($authResponse -match '<value><(?:i4|int)>(\d+)</(?:i4|int)></value>') {
            $uid = [int]$matches[1]
        } elseif ($authResponse -match '<fault>') {
            # XML-RPC fault response
            if ($authResponse -match '<string>(.*?)</string>') {
                $faultMsg = $matches[1]
                throw "XML-RPC Authentication Fault: $faultMsg"
            }
            throw "XML-RPC Authentication Fault (unknown error)"
        } else {
            Write-Host "  Debug: Response was: $authResponse" -ForegroundColor Gray
            throw "Unexpected response format from authentication"
        }
        
        if (-not $uid -or $uid -eq 0) {
            throw "Authentication failed. Invalid username or password, or database not found."
        }
    } catch {
        $errorMsg = $_.Exception.Message
        Write-Host "  Error: $errorMsg" -ForegroundColor Red
        
        # Check if it's a 404 error
        if ($errorMsg -match "404") {
            Write-Host ""
            Write-Host "❌ XML-RPC is not available (404 Not Found)" -ForegroundColor Red
            Write-Host ""
            Write-Host "XML-RPC might be disabled in Odoo 19. To enable it:" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Option 1: Enable XML-RPC in Odoo configuration" -ForegroundColor Cyan
            Write-Host "  1. Edit your Odoo configuration file (usually odoo.conf)" -ForegroundColor Gray
            Write-Host "  2. Add or uncomment this line:" -ForegroundColor Gray
            Write-Host "     xmlrpc = True" -ForegroundColor White
            Write-Host "  3. Restart Odoo server" -ForegroundColor Gray
            Write-Host ""
            Write-Host "Option 2: Use Odoo UI instead (Recommended)" -ForegroundColor Cyan
            Write-Host "  1. Open: $ODOO_URL/web" -ForegroundColor Gray
            Write-Host "  2. Go to: Odoo 14 Migration > Estimation" -ForegroundColor Gray
            Write-Host "  3. Click the '⋮' (Action) menu in the top right" -ForegroundColor Gray
            Write-Host "  4. Select: 'Process Queue Jobs Now'" -ForegroundColor Gray
            Write-Host ""
            Write-Host "The queue jobs will be processed automatically by the cron job runner" -ForegroundColor Gray
            Write-Host "or you can trigger them manually from the UI." -ForegroundColor Gray
            Write-Host ""
        } else {
            Write-Host ""
            Write-Host "Please verify:" -ForegroundColor Yellow
            Write-Host "  1. Odoo server is running on $ODOO_URL" -ForegroundColor Gray
            Write-Host "  2. Database name '$DATABASE' is correct" -ForegroundColor Gray
            Write-Host "  3. Username and password are correct" -ForegroundColor Gray
            Write-Host "  4. XML-RPC is enabled in Odoo configuration" -ForegroundColor Gray
        }
        throw $errorMsg
    }
    
    Write-Host "✅ Authenticated successfully (UID: $uid)" -ForegroundColor Green
    Write-Host ""
    
    # Get any record to call the method on (the method works on any recordset)
    Write-Host "Finding estimation migration records..." -ForegroundColor Yellow
    $objectUrl = "$ODOO_URL/xmlrpc/2/object"
    
    # Search for records using execute_kw via XML-RPC
    $searchXml = @"
<?xml version='1.0'?>
<methodCall>
  <methodName>execute_kw</methodName>
  <params>
    <param><value><string>$DATABASE</string></value></param>
    <param><value><int>$uid</int></value></param>
    <param><value><string>$PASSWORD</string></value></param>
    <param><value><string>estimation.migration.line</string></value></param>
    <param><value><string>search</string></value></param>
    <param><value><array><data><value><array><data></data></array></value></data></array></value></param>
    <param><value><struct><member><name>limit</name><value><int>1</int></value></member></struct></value></param>
  </params>
</methodCall>
"@
    
    $searchResponse = Invoke-OdooXMLRPC -Url $objectUrl -XmlBody $searchXml
    $records = @()
    if ($searchResponse -match '<value><array><data>(.*?)</data></array></value>') {
        $arrayContent = $matches[1]
        while ($arrayContent -match '<value><(?:i4|int)>(\d+)</(?:i4|int)></value>') {
            $records += [int]$matches[1]
            $arrayContent = $arrayContent -replace '<value><(?:i4|int)>\d+</(?:i4|int)></value>', '', 1
        }
    }
    
    if ($records.Count -eq 0) {
        Write-Host "⚠️  No estimation migration records found." -ForegroundColor Yellow
        Write-Host "   Please upload Excel file first: Odoo 14 Migration > Estimation > Upload Excel" -ForegroundColor Gray
        Write-Host ""
        exit 0
    }
    
    Write-Host "✅ Found records. Triggering queue job runner..." -ForegroundColor Green
    Write-Host ""
    
    # Call the action_trigger_queue_job_runner method on the recordset
    try {
        # Build XML for execute_kw call - pass records array
        $recordsXml = ""
        foreach ($recordId in $records) {
            $recordsXml += "<value><int>$recordId</int></value>"
        }
        
        $callXml = @"
<?xml version='1.0'?>
<methodCall>
  <methodName>execute_kw</methodName>
  <params>
    <param><value><string>$DATABASE</string></value></param>
    <param><value><int>$uid</int></value></param>
    <param><value><string>$PASSWORD</string></value></param>
    <param><value><string>estimation.migration.line</string></value></param>
    <param><value><string>action_trigger_queue_job_runner</string></value></param>
    <param><value><array><data><value><array><data>$recordsXml</data></array></value></data></array></value></param>
    <param><value><struct></struct></value></param>
  </params>
</methodCall>
"@
        
        $null = Invoke-OdooXMLRPC -Url $objectUrl -XmlBody $callXml
        
        Write-Host "✅ Queue job runner triggered successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Status: Queue jobs are now being processed." -ForegroundColor Gray
        Write-Host ""
        Write-Host "Monitor progress in Odoo UI:" -ForegroundColor Yellow
        Write-Host "  - Go to: Odoo 14 Migration > Estimation (list view)" -ForegroundColor Gray
        Write-Host "  - Or: Settings > Technical > Automation > Queue Jobs" -ForegroundColor Gray
        Write-Host ""
    } catch {
        $errorMsg = $_.Exception.Message
        Write-Host "❌ Error triggering queue job runner: $errorMsg" -ForegroundColor Red
        Write-Host ""
        Write-Host "Alternative: Use the Odoo UI instead:" -ForegroundColor Yellow
        Write-Host "  1. Go to: $ODOO_URL/web" -ForegroundColor Gray
        Write-Host "  2. Navigate to: Odoo 14 Migration > Estimation > Process Queue Jobs Now" -ForegroundColor Gray
        Write-Host "  3. Click the button to trigger queue job processing" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Or jobs will be processed automatically by the cron job runner" -ForegroundColor Gray
        Write-Host "  (runs every minute by default)" -ForegroundColor Gray
        Write-Host ""
    }
    
} catch {
    Write-Host ""
    Write-Host "ERROR: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Ensure Odoo server is running on $ODOO_URL" -ForegroundColor Gray
    Write-Host "  2. Verify database name '$DATABASE' is correct" -ForegroundColor Gray
    Write-Host "  3. Check that queue_job module is installed and working" -ForegroundColor Gray
    Write-Host ""
    exit 1
}
