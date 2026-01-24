# PowerShell script for CRM Lead Migration
# Triggers queue job runner to process CRM lead migration queue jobs
#
# Prerequisites:
# 1. Upload Excel file in Odoo UI (CRM Leads > Upload Excel)
# 2. Select leads and click "Migrate Selected" in Odoo UI
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
    Write-Host "=== CRM Lead Migration Queue Processor ===" -ForegroundColor Cyan
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
        
        if ($uid -eq 0) {
            throw "Authentication failed: Invalid credentials or database"
        }
        
        Write-Host "  ✅ Authenticated successfully (UID: $uid)" -ForegroundColor Green
        Write-Host ""
        
    } catch {
        Write-Host "  ❌ ERROR: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "Troubleshooting:" -ForegroundColor Yellow
        Write-Host "1. Ensure Odoo server is running on $ODOO_URL" -ForegroundColor Gray
        Write-Host "2. Verify database name '$DATABASE' is correct" -ForegroundColor Gray
        Write-Host "3. Check that queue_job module is installed and working" -ForegroundColor Gray
        exit 1
    }
    
    # Call the action_trigger_queue_job_runner method
    $objectUrl = "$ODOO_URL/xmlrpc/2/object"
    
    Write-Host "Triggering queue job runner for CRM leads..." -ForegroundColor Yellow
    
    # Call execute_kw to trigger the queue job runner
    $executeXml = @"
<?xml version='1.0' encoding='UTF-8'?>
<methodCall>
  <methodName>execute_kw</methodName>
  <params>
    <param><value><string>$DATABASE</string></value></param>
    <param><value><int>$uid</int></value></param>
    <param><value><string>$PASSWORD</string></value></param>
    <param><value><string>crm.lead.migration.line</string></value></param>
    <param><value><string>action_trigger_queue_job_runner</string></value></param>
    <param><value><array>
      <data>
        <value><array><data></data></array></value>
      </data>
    </array></value></param>
    <param><value><struct></struct></value></param>
  </params>
</methodCall>
"@
    
    try {
        $executeResponse = Invoke-OdooXMLRPC -Url $objectUrl -XmlBody $executeXml
        
        # Check for faults
        if ($executeResponse -match '<fault>') {
            if ($executeResponse -match '<string>(.*?)</string>') {
                $faultMsg = $matches[1]
                throw "XML-RPC Fault: $faultMsg"
            }
            throw "XML-RPC Fault (unknown error)"
        }
        
        Write-Host "  ✅ Queue job runner triggered successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "The queue job runner will now process pending CRM lead migration jobs." -ForegroundColor Cyan
        Write-Host "Check the queue status in Odoo: Settings → Technical → Queue → Jobs" -ForegroundColor Gray
        Write-Host ""
        
    } catch {
        Write-Host "  ❌ ERROR: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "Troubleshooting:" -ForegroundColor Yellow
        Write-Host "1. Ensure queue_job module is installed" -ForegroundColor Gray
        Write-Host "2. Ensure queue_job_cron_jobrunner module is installed" -ForegroundColor Gray
        Write-Host "3. Check that CRM lead migration line records exist and have pending jobs" -ForegroundColor Gray
        exit 1
    }
    
} catch {
    Write-Host ""
    Write-Host "FATAL ERROR: $_" -ForegroundColor Red
    exit 1
}

