# PowerShell script to Delete Draft Customer Invoices
# Uses Odoo JSON-RPC directly to avoid Python dependencies

param(
    [string]$Url = "https://metro.equdaierp.com",
    [string]$Db = "metrodb",
    [string]$User = "admin",
    [string]$Password = "Amaze@321",
    [int]$Limit = 100
)

# Colors for output
function Write-Status {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Invoke-OdooRpc {
    param(
        [string]$Endpoint,
        [hashtable]$Params
    )
    
    $rpcPayload = @{
        jsonrpc = "2.0"
        method  = "call"
        params  = $Params
        id      = Get-Random
    }
    
    try {
        $jsonBody = $rpcPayload | ConvertTo-Json -Depth 10 -Compress
        $response = Invoke-WebRequest -Uri "$Url$Endpoint" -Method Post -Body $jsonBody -WebSession $Script:WebSession -ContentType "application/json" -ErrorAction Stop
        $result = $response.Content | ConvertFrom-Json
        
        if ($result.error) {
            throw $result.error.data.message
        }
        
        return $result.result
    }
    catch {
        throw $_
    }
}

try {
    Write-Status "=== Delete Draft Customer Invoices ===" "Cyan"
    Write-Status "URL: $Url" "Gray"
    Write-Status "Database: $Db" "Gray"
    Write-Status ""

    $Script:WebSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession

    # Authenticate
    Write-Status "Authenticating..." "Yellow"
    $authResult = Invoke-OdooRpc -Endpoint "/web/session/authenticate" -Params @{
        db       = $Db
        login    = $User
        password = $Password
    }
    
    if (-not $authResult.uid) {
        throw "Authentication failed"
    }
    Write-Status "✅ Authenticated as User ID: $($authResult.uid)" "Green"
    Write-Status ""

    while ($true) {
        # Search Draft Invoices
        Write-Status "Searching for draft invoices (Limit: $Limit)..." "Yellow"
        
        $domain = @(
            @("move_type", "=", "out_invoice"),
            @("state", "=", "draft")
        )

        $searchResult = Invoke-OdooRpc -Endpoint "/web/dataset/call_kw" -Params @{
            model  = "account.move"
            method = "search"
            args   = @(, $domain)
            kwargs = @{ limit = $Limit }
        }

        if (-not $searchResult -or $searchResult.Count -eq 0) {
            Write-Status "✅ No more draft customer invoices found." "Green"
            break
        }

        $count = $searchResult.Count
        Write-Status "Found $count draft invoices. Deleting..." "Yellow"

        # Delete (Unlink)
        try {
            $null = Invoke-OdooRpc -Endpoint "/web/dataset/call_kw" -Params @{
                model  = "account.move"
                method = "unlink"
                args   = @($searchResult)
                kwargs = @{}
            }
            Write-Status "✅ Successfully deleted $count invoices." "Green"
        }
        catch {
            Write-Status "❌ Batch delete failed: $_" "Red"
            Write-Status "Trying one by one..." "Yellow"
             
            foreach ($id in $searchResult) {
                try {
                    $null = Invoke-OdooRpc -Endpoint "/web/dataset/call_kw" -Params @{
                        model  = "account.move"
                        method = "unlink"
                        args   = @(@($id))
                        kwargs = @{}
                    }
                    Write-Status "  Deleted invoice ID $id" "Gray"
                }
                catch {
                    Write-Status "  ❌ Failed to delete invoice ID $id : $_" "Red"
                }
            }
        }
        
        Start-Sleep -Seconds 1
    }

}
catch {
    Write-Status "ERROR: $_" "Red"
    exit 1
}
