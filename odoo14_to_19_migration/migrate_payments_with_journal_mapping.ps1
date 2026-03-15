<#
.SYNOPSIS
    Odoo Payment Migration Report
    
.DESCRIPTION
    Migrate customer/vendor payments from SOURCE Odoo 19 database to TARGET Odoo 19 database
    using an existing Journal Mapping CSV file to map journal_id.
    
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\migrate_payments_with_journal_mapping.ps1 -PathToJournalMapCsv .\output\journal_mapping\JournalMapping_AJMAN_TO_AJMAN_20260303_1623.csv
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory = $true)]
    [string]$PathToJournalMapCsv,
    
    [string]$OutputDir = ".\output\payment_migration\",
    [switch]$DryRun = $true,
    [switch]$AutoPost = $true,
    [switch]$IncludeDraft = $false,
    [switch]$Resume = $false,
    [int]$Limit = 0,
    [string]$FromDate,
    [string]$ToDate,
    [switch]$UseEnvCreds = $false,
    [switch]$OpenAfter = $false
)

# ---------------------------------------------------------
# Security Note:
# Storing plaintext passwords in scripts is not recommended.
# Use the -UseEnvCreds switch to safely inject credentials 
# through environment variables:
# 
# ODOO_URL_SRC, ODOO_DB_SRC, ODOO_USER_SRC, ODOO_PASS_SRC
# ODOO_URL_TGT, ODOO_DB_TGT, ODOO_USER_TGT, ODOO_PASS_TGT
# ---------------------------------------------------------

$ErrorActionPreference = "Stop"

# --- Hardcoded Credentials (used if env vars not provided) ---
$URL_TGT = "https://metro.equdaierp.com"
$DB_TGT = "newdb"
$USER_TGT = "admin"
$PASS_TGT = "Amaze@321"

$URL_SRC = "https://metro.equdaierp.com"
$DB_SRC = "metrodb"
$USER_SRC = "admin"
$PASS_SRC = "Amaze@321"

if ($UseEnvCreds) {
    if ($env:ODOO_URL_SRC) { $URL_SRC = $env:ODOO_URL_SRC }
    if ($env:ODOO_DB_SRC) { $DB_SRC = $env:ODOO_DB_SRC }
    if ($env:ODOO_USER_SRC) { $USER_SRC = $env:ODOO_USER_SRC }
    if ($env:ODOO_PASS_SRC) { $PASS_SRC = $env:ODOO_PASS_SRC }
    
    if ($env:ODOO_URL_TGT) { $URL_TGT = $env:ODOO_URL_TGT }
    if ($env:ODOO_DB_TGT) { $DB_TGT = $env:ODOO_DB_TGT }
    if ($env:ODOO_USER_TGT) { $USER_TGT = $env:ODOO_USER_TGT }
    if ($env:ODOO_PASS_TGT) { $PASS_TGT = $env:ODOO_PASS_TGT }
}

# ---------------------------------------------------------
# 1) CONNECTIVITY / XML-RPC HELPERS
# ---------------------------------------------------------

function ConvertTo-XmlRpcType {
    param($Value)
    if ($null -eq $Value) { return "<value><boolean>0</boolean></value>" }
    if ($Value -is [bool]) { $v = if ($Value) { 1 }else { 0 }; return "<value><boolean>$v</boolean></value>" }
    if ($Value -is [int] -or $Value -is [long]) { return "<value><int>$Value</int></value>" }
    if ($Value -is [double] -or $Value -is [float]) { return "<value><double>$Value</double></value>" }
    if ($Value -is [string]) {
        $esc = $Value.Replace("&", "&amp;").Replace("<", "&lt;").Replace(">", "&gt;").Replace('"', "&quot;").Replace("'", "&apos;")
        return "<value><string>$esc</string></value>"
    }
    if ($Value -is [System.Collections.IDictionary]) {
        $res = "<value><struct>"
        foreach ($key in $Value.Keys) {
            $valXml = ConvertTo-XmlRpcType $Value[$key]
            $res += "<member><name>$key</name>$valXml</member>"
        }
        $res += "</struct></value>"
        return $res
    }
    if ($Value -is [System.Collections.IEnumerable]) {
        $res = "<value><array><data>"
        foreach ($item in $Value) { $res += ConvertTo-XmlRpcType $item }
        $res += "</data></array></value>"
        return $res
    }
    $esc = $Value.ToString().Replace("&", "&amp;").Replace("<", "&lt;").Replace(">", "&gt;").Replace('"', "&quot;").Replace("'", "&apos;")
    return "<value><string>$esc</string></value>"
}

function ConvertFrom-XmlRpcType {
    param([System.Xml.XmlNode]$ValueNode)
    $child = $ValueNode.FirstChild
    if ($child -eq $null) { return $ValueNode.InnerText }
    
    switch ($child.Name) {
        "boolean" { return ($child.InnerText -eq "1") }
        "int" { return [int]$child.InnerText }
        "i4" { return [int]$child.InnerText }
        "double" { return [double]$child.InnerText }
        "string" { return $child.InnerText }
        "array" {
            $arr = @()
            if ($child.data -and $child.data.value) {
                foreach ($v in $child.data.SelectNodes("value")) {
                    $arr += ConvertFrom-XmlRpcType $v
                }
            }
            return $arr
        }
        "struct" {
            $obj = @{}
            if ($child.member) {
                foreach ($m in $child.SelectNodes("member")) {
                    $obj[$m.name] = ConvertFrom-XmlRpcType $m.value
                }
            }
            return $obj
        }
    }
    return $child.InnerText
}

function Invoke-OdooXmlRpc {
    param(
        [string]$Url,
        [string]$MethodName,
        [array]$Params
    )
    $xml = "<?xml version='1.0'?><methodCall><methodName>$MethodName</methodName><params>"
    foreach ($p in $Params) {
        $xml += "<param>" + (ConvertTo-XmlRpcType $p) + "</param>"
    }
    $xml += "</params></methodCall>"
    
    Write-Verbose "RPC CALL: $Url -> $MethodName"
    try {
        $resp = Invoke-WebRequest -Uri $Url -Method Post -Body $xml -ContentType "text/xml" -UseBasicParsing
        [xml]$doc = $resp.Content
        if ($doc.methodResponse.fault) {
            $fault = ConvertFrom-XmlRpcType $doc.methodResponse.fault.value
            throw "XML-RPC Fault: $($fault.faultString)"
        }
        return ConvertFrom-XmlRpcType $doc.methodResponse.params.param.value
    }
    catch {
        throw "Failed calling $MethodName on $Url : $_"
    }
}

function Connect-Odoo {
    param($Url, $Db, $User, $Pass)
    $loginUrl = "$Url/xmlrpc/2/common"
    Write-Host "Connecting to Odoo Database: $Db at $Url ..." -ForegroundColor Cyan
    $uid = Invoke-OdooXmlRpc -Url $loginUrl -MethodName "authenticate" -Params @($Db, $User, $Pass, @{})
    if (-not $uid -or $uid -is [bool]) { throw "Authentication failed to $Db (returned false/null)." }
    Write-Host "Connected successfully. UID: $uid" -ForegroundColor Green
    return @{
        Url = $Url; Db = $Db; User = $User; Pass = $Pass; Uid = $uid
    }
}

function Invoke-OdooSearchRead {
    param($Conn, $Model, $Domain, $Fields, $Limit = 0)
    $objectUrl = "$($Conn.Url)/xmlrpc/2/object"
    
    $kwargs = @{ fields = $Fields }
    if ($Limit -gt 0) { $kwargs['limit'] = $Limit }
    
    $argsList = New-Object System.Collections.ArrayList
    $domainList = New-Object System.Collections.ArrayList
    foreach ($c in $Domain) {
        if ($c -is [array]) {
            $crit = New-Object System.Collections.ArrayList
            foreach ($i in $c) { $crit.Add($i) | Out-Null }
            $domainList.Add($crit) | Out-Null
        }
        else {
            $domainList.Add($c) | Out-Null
        }
    }
    $argsList.Add($domainList) | Out-Null
    
    $params = @( $Conn.Db, $Conn.Uid, $Conn.Pass, $Model, "search_read", $argsList, $kwargs )
    return Invoke-OdooXmlRpc -Url $objectUrl -MethodName "execute_kw" -Params $params
}

function Invoke-OdooSearch {
    param($Conn, $Model, $Domain, $Limit = 0)
    $objectUrl = "$($Conn.Url)/xmlrpc/2/object"
    
    $kwargs = @{}
    if ($Limit -gt 0) { $kwargs['limit'] = $Limit }
    
    $argsList = New-Object System.Collections.ArrayList
    $domainList = New-Object System.Collections.ArrayList
    foreach ($c in $Domain) {
        if ($c -is [array]) {
            $crit = New-Object System.Collections.ArrayList
            foreach ($i in $c) { $crit.Add($i) | Out-Null }
            $domainList.Add($crit) | Out-Null
        }
        else {
            $domainList.Add($c) | Out-Null
        }
    }
    $argsList.Add($domainList) | Out-Null
    
    $params = @( $Conn.Db, $Conn.Uid, $Conn.Pass, $Model, "search", $argsList, $kwargs )
    return Invoke-OdooXmlRpc -Url $objectUrl -MethodName "execute_kw" -Params $params
}

function Invoke-OdooRead {
    param($Conn, $Model, $Ids, $Fields)
    $objectUrl = "$($Conn.Url)/xmlrpc/2/object"
    $kwargs = @{ fields = $Fields }
    
    $argsList = New-Object System.Collections.ArrayList
    $idsList = New-Object System.Collections.ArrayList
    foreach ($i in $Ids) { $idsList.Add($i) | Out-Null }
    $argsList.Add($idsList) | Out-Null
    
    $params = @( $Conn.Db, $Conn.Uid, $Conn.Pass, $Model, "read", $argsList, $kwargs )
    return Invoke-OdooXmlRpc -Url $objectUrl -MethodName "execute_kw" -Params $params
}

function Invoke-OdooCreate {
    param($Conn, $Model, $Values)
    $objectUrl = "$($Conn.Url)/xmlrpc/2/object"
    
    $argsList = New-Object System.Collections.ArrayList
    $argsList.Add($Values) | Out-Null
    
    $params = @( $Conn.Db, $Conn.Uid, $Conn.Pass, $Model, "create", $argsList )
    return Invoke-OdooXmlRpc -Url $objectUrl -MethodName "execute_kw" -Params $params
}

function Invoke-OdooExecute {
    param($Conn, $Model, $Method, $Ids, $Kwargs = @{})
    $objectUrl = "$($Conn.Url)/xmlrpc/2/object"
    
    $argsList = New-Object System.Collections.ArrayList
    $idsList = New-Object System.Collections.ArrayList
    if ($Ids) { foreach ($i in $Ids) { $idsList.Add($i) | Out-Null } }
    $argsList.Add($idsList) | Out-Null
    
    $params = @( $Conn.Db, $Conn.Uid, $Conn.Pass, $Model, $Method, $argsList, $Kwargs )
    return Invoke-OdooXmlRpc -Url $objectUrl -MethodName "execute_kw" -Params $params
}

function Get-OdooFields {
    param($Conn, $Model)
    $objectUrl = "$($Conn.Url)/xmlrpc/2/object"
    $params = @( $Conn.Db, $Conn.Uid, $Conn.Pass, $Model, "fields_get", @(), @{} )
    return Invoke-OdooXmlRpc -Url $objectUrl -MethodName "execute_kw" -Params $params
}


# ---------------------------------------------------------
# 2) INTERACTIVE SELECTION
# ---------------------------------------------------------

function Select-Company {
    param($Title, $Companies)
    if (-not $Companies -or $Companies.Count -eq 0) { throw "No companies found for $Title." }
    
    $selected = $null
    
    # Check if Out-GridView is available
    if (Get-Command Out-GridView -ErrorAction SilentlyContinue) {
        $choice = $Companies | Select-Object id, name | Out-GridView -Title $Title -PassThru
        if ($choice) {
            $selected = $Companies | Where-Object { $_.id -eq $choice.id }
        }
    }
    
    if (-not $selected) {
        Write-Host "--- $Title ---" -ForegroundColor Yellow
        for ($i = 0; $i -lt $Companies.Count; $i++) {
            Write-Host "$($i+1). $($Companies[$i].name) (ID: $($Companies[$i].id))"
        }
        while ($true) {
            $choice = Read-Host "Select a company number (1 - $($Companies.Count))"
            if ([int]::TryParse($choice, [ref]$null)) {
                $idx = [int]$choice - 1
                if ($idx -ge 0 -and $idx -lt $Companies.Count) {
                    $selected = $Companies[$idx]
                    break
                }
            }
            Write-Warning "Invalid choice. Try again."
        }
    }
    
    if ($selected -is [array]) { $selected = $selected[0] }
    return $selected
}

# ---------------------------------------------------------
# UTILS & HELPERS
# ---------------------------------------------------------

function Get-M2oId {
    param($Field)
    if ($null -eq $Field) { return $null }
    if ($Field -is [array] -and $Field.Count -eq 2) { return [int]$Field[0] }
    if ($Field -is [int]) { return $Field }
    return $null
}

function Get-M2oName {
    param($Field)
    if ($null -eq $Field) { return "" }
    if ($Field -is [array] -and $Field.Count -eq 2) { return "$($Field[1])" }
    return ""
}

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------

try {
    Write-Host "========== ODOO PAYMENT MIGRATION TOOL ==========" -ForegroundColor White -BackgroundColor DarkBlue
    if ($DryRun) { Write-Host "--- RUNNING IN DRY-RUN MODE ---" -ForegroundColor Yellow }

    # Connect to Source and Target
    $srcConn = Connect-Odoo -Url $URL_SRC -Db $DB_SRC -User $USER_SRC -Pass $PASS_SRC
    $tgtConn = Connect-Odoo -Url $URL_TGT -Db $DB_TGT -User $USER_TGT -Pass $PASS_TGT
    
    # 3) Load Mapping CSV
    if (!(Test-Path $PathToJournalMapCsv)) {
        throw "Journal map CSV not found at: $PathToJournalMapCsv"
    }
    $csvData = Import-Csv $PathToJournalMapCsv
    $journalMap = @{}
    foreach ($row in $csvData) {
        $tgtId = "$($row.TargetJournalId)".Trim()
        if ($tgtId -match '^\d+$') {
            $journalMap[[int]$row.SourceJournalId] = [int]$tgtId
        }
    }
    Write-Host "Loaded $($journalMap.Count) mapped journals from CSV." -ForegroundColor Green
    
    # 2) Interactive Selection
    $srcCompanies = Invoke-OdooSearchRead -Conn $srcConn -Model "res.company" -Domain @() -Fields @("id", "name")
    $tgtCompanies = Invoke-OdooSearchRead -Conn $tgtConn -Model "res.company" -Domain @() -Fields @("id", "name")
    
    $selSrcComp = Select-Company -Title "Select SOURCE Company ($DB_SRC)" -Companies $srcCompanies
    Write-Host "Selected Source Company: $($selSrcComp.name)" -ForegroundColor Green
    
    $selTgtComp = Select-Company -Title "Select TARGET Company/Branch ($DB_TGT)" -Companies $tgtCompanies
    Write-Host "Selected Target Company: $($selTgtComp.name)" -ForegroundColor Green

    # 11) Resume / Checkpoint
    if (!(Test-Path $OutputDir)) { New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null }
    $safeS = $selSrcComp.name -replace '[^a-zA-Z0-9]', '_'
    $safeT = $selTgtComp.name -replace '[^a-zA-Z0-9]', '_'
    $checkpointFile = Join-Path $OutputDir "checkpoint_${safeS}_to_${safeT}.json"
    
    $migratedIds = @()
    if ($Resume -and (Test-Path $checkpointFile)) {
        $cp = Get-Content $checkpointFile | ConvertFrom-Json
        if ($cp.migrated_ids) { $migratedIds = $cp.migrated_ids }
        Write-Host "Resuming... found $($migratedIds.Count) already migrated payment IDs in checkpoint." -ForegroundColor Yellow
    }
    
    # 4) Extract payments from SOURCE
    Write-Host "Fetching payments from Source..." -ForegroundColor Cyan
    $requestedFields = @("id", "name", "payment_type", "partner_type", "amount", "currency_id", 
        "date", "ref", "journal_id", "partner_id", "destination_account_id", 
        "payment_method_line_id", "state", "move_id", "communication", "company_id")
                         
    $availableFields = Get-OdooFields -Conn $srcConn -Model "account.payment"
    $realFields = @()
    foreach ($f in $requestedFields) {
        if ($availableFields.ContainsKey($f)) { $realFields += $f }
    }

    $domain = @( , @("company_id", "=", $selSrcComp.id) )
    if (!$IncludeDraft) {
        $domain += , @("state", "in", @("posted", "paid", "in_process", "reconciled"))
    }
    if ($FromDate) { $domain += , @("date", ">=", $FromDate) }
    if ($ToDate) { $domain += , @("date", "<=", $ToDate) }
    
    $srcPayments = Invoke-OdooSearchRead -Conn $srcConn -Model "account.payment" -Domain $domain -Fields $realFields -Limit $Limit
    Write-Host "Found $($srcPayments.Count) payments to process in Source." -ForegroundColor Green

    # Helpers for mapping Caches
    $partnerCache = @{}
    $currencyCache = @{}
    $paymentMethodLineCache = @{}
    $tgtCompanyCurrency = $null

    $results = @()
    
    # Pre-fetch target company default currency
    $tgtCompDetails = Invoke-OdooRead -Conn $tgtConn -Model "res.company" -Ids @($selTgtComp.id) -Fields @("currency_id")
    if ($tgtCompDetails -and $tgtCompDetails[0].currency_id) {
        $tgtCompanyCurrency = Get-M2oId $tgtCompDetails[0].currency_id
    }

    foreach ($p in $srcPayments) {
        $status = "ERROR"
        $reason = ""
        $tgtPaymentId = $null
        $mappedTgtJournalId = $null
        
        try {
            if ($migratedIds -contains $p.id) {
                Write-Verbose "Skipping Payment $($p.id) ($($p.name)) - already migrated according to checkpoint."
                continue
            }

            Write-Host "Processing Payment ID $($p.id) - $($p.name) ..."
            
            # 7) Journal mapping
            $srcJrnId = Get-M2oId $p.journal_id
            if (-not ($srcJrnId) -or -not ($journalMap.ContainsKey($srcJrnId))) {
                $status = "SKIPPED"
                $reason = "SKIPPED_NO_JOURNAL_MAPPING"
                throw "No matched target journal for Source Journal ID $srcJrnId"
            }
            $mappedTgtJournalId = $journalMap[$srcJrnId]
            
            # 5) Partner mapping strategy
            $tgtPartnerId = $null
            $srcPartnerId = Get-M2oId $p.partner_id
            if ($srcPartnerId) {
                if ($partnerCache.ContainsKey($srcPartnerId)) {
                    $tgtPartnerId = $partnerCache[$srcPartnerId]
                }
                else {
                    $reqPartnerFields = @("name", "vat", "email", "phone", "mobile", "company_type", "company_id")
                    $availPartnerFields = Get-OdooFields -Conn $srcConn -Model "res.partner"
                    $realPartnerFields = @()
                    foreach ($f in $reqPartnerFields) {
                        if ($availPartnerFields.ContainsKey($f)) { $realPartnerFields += $f }
                    }
                    
                    $srcPartnerDetails = Invoke-OdooRead -Conn $srcConn -Model "res.partner" -Ids @($srcPartnerId) -Fields $realPartnerFields
                    if ($srcPartnerDetails) {
                        $sp = $srcPartnerDetails[0]
                        $spName = "$($sp.name)".ToLower().Trim()
                        
                        # Try map by active Company Name context
                        if ($sp.company_id) {
                            $spCompanyNameMatch = Get-M2oName $sp.company_id
                            if ($spCompanyNameMatch) {
                                # Company based matching logic requested in instructions "Company Mapping Using Company Name field"
                                # Although in strict mapping, partner is global or company-bound. We map to the selected TGT company.
                            }
                        }

                        # 1. Match by VAT
                        if ($sp.vat) {
                            $found = Invoke-OdooSearch -Conn $tgtConn -Model "res.partner" -Domain @(, @("vat", "=", $sp.vat)) -Limit 1
                            if ($found) { $tgtPartnerId = $found[0] }
                        }
                        # 2. Match by Email
                        if (-not $tgtPartnerId -and $sp.email) {
                            $found = Invoke-OdooSearch -Conn $tgtConn -Model "res.partner" -Domain @(, @("email", "=", $sp.email)) -Limit 1
                            if ($found) { $tgtPartnerId = $found[0] }
                        }
                        # 3. Match by Name Exact
                        if (-not $tgtPartnerId -and $spName) {
                            $foundSearch = Invoke-OdooSearchRead -Conn $tgtConn -Model "res.partner" -Domain @(, @("name", "ilike", $sp.name)) -Fields @("id", "name")
                            foreach ($f in $foundSearch) {
                                if ("$($f.name)".ToLower().Trim() -eq $spName) {
                                    $tgtPartnerId = $f.id
                                    break
                                }
                            }
                        }
                        
                        # 4. Create in TARGET if not found
                        if (-not $tgtPartnerId -and -not $DryRun) {
                            Write-Verbose "Partner not found in target. Creating: $($sp.name)"
                            $pVals = @{
                                name       = $sp.name
                                company_id = $selTgtComp.id
                            }
                            if ($sp.vat) { $pVals.vat = $sp.vat }
                            if ($sp.email) { $pVals.email = $sp.email }
                            # Dynamically determine if 'mobile' exists in target
                            $availTgtFields = Get-OdooFields -Conn $tgtConn -Model "res.partner"
                            if ($sp.mobile -and $availTgtFields.ContainsKey("mobile")) { $pVals.mobile = $sp.mobile }
                            if ($sp.company_type) { $pVals.company_type = $sp.company_type }
                            
                            $tgtPartnerId = Invoke-OdooCreate -Conn $tgtConn -Model "res.partner" -Values $pVals
                            Write-Host "Created new partner in target ID: $tgtPartnerId" -ForegroundColor Magenta
                        }
                        elseif (-not $tgtPartnerId -and $DryRun) {
                            $tgtPartnerId = -999 # Dummy ID for dry run
                            Write-Verbose "Partner not found in target. [DRY RUN] Would create: $($sp.name)"
                        }
                    }
                    if ($tgtPartnerId) { $partnerCache[$srcPartnerId] = $tgtPartnerId }
                }
            }

            # 6) Currency mapping
            $tgtCurrencyId = $tgtCompanyCurrency
            $srcCurrId = Get-M2oId $p.currency_id
            if ($srcCurrId) {
                if ($currencyCache.ContainsKey($srcCurrId)) {
                    $tgtCurrencyId = $currencyCache[$srcCurrId]
                }
                else {
                    $srcCurrName = Get-M2oName $p.currency_id
                    if ($srcCurrName) {
                        $foundCurr = Invoke-OdooSearch -Conn $tgtConn -Model "res.currency" -Domain @(, @("name", "=", $srcCurrName)) -Limit 1
                        if ($foundCurr) {
                            $tgtCurrencyId = $foundCurr[0]
                            $currencyCache[$srcCurrId] = $tgtCurrencyId
                        }
                        else {
                            Write-Verbose "Currency $srcCurrName not found in target. Falling back to target company currency."
                        }
                    }
                }
            }

            # 8) Payment method line mapping
            $tgtPmlId = $null
            $srcPmlId = Get-M2oId $p.payment_method_line_id
            if ($srcPmlId) {
                $cacheKey = "$srcPmlId-$mappedTgtJournalId"
                if ($paymentMethodLineCache.ContainsKey($cacheKey)) {
                    $tgtPmlId = $paymentMethodLineCache[$cacheKey]
                }
                else {
                    $srcPmlName = Get-M2oName $p.payment_method_line_id
                    if ($srcPmlName) {
                        # Find in target matching journal and name
                        $pmlDomain = @( , @("journal_id", "=", $mappedTgtJournalId) )
                        if ($p.payment_type) { $pmlDomain += , @("payment_type", "=", $p.payment_type) }
                        
                        $foundPmls = Invoke-OdooSearchRead -Conn $tgtConn -Model "account.payment.method.line" -Domain $pmlDomain -Fields @("id", "name")
                        foreach ($f in $foundPmls) {
                            if ("$($f.name)".ToLower().Trim() -eq $srcPmlName.ToLower().Trim()) {
                                $tgtPmlId = $f.id
                                break
                            }
                        }
                        if ($tgtPmlId) {
                            $paymentMethodLineCache[$cacheKey] = $tgtPmlId
                        }
                        else {
                            Write-Verbose "Payment method line '$srcPmlName' not found in Target Journal $mappedTgtJournalId. Will attempt to leave unset."
                        }
                    }
                }
            }

            # 10) Duplicate detection
            $tgtPayFields = Get-OdooFields -Conn $tgtConn -Model "account.payment"
            
            $dupDomain = @(
                , @("partner_id", "=", $tgtPartnerId),
                , @("journal_id", "=", $mappedTgtJournalId),
                , @("amount", "=", $p.amount),
                , @("date", "=", $p.date)
            )
            if ($p.payment_type -and $tgtPayFields.ContainsKey("payment_type")) {
                $dupDomain += , @("payment_type", "=", $p.payment_type)
            }
            
            $refOrComm = if ($p.ref) { $p.ref } elseif ($p.communication) { $p.communication } else { $null }
            if ($refOrComm) {
                # Odoo 14 has communication usually, Odoo 19 has ref. Let's check ref if it exists in tgt.
                if ($tgtPayFields.ContainsKey("ref")) {
                    $dupDomain += , @("ref", "=", $refOrComm)
                }
                elseif ($tgtPayFields.ContainsKey("communication")) {
                    $dupDomain += , @("communication", "=", $refOrComm)
                }
            }
            
            $dupFound = Invoke-OdooSearch -Conn $tgtConn -Model "account.payment" -Domain $dupDomain -Limit 1
            if ($dupFound) {
                $status = "SKIPPED"
                $reason = "SKIPPED_DUPLICATE"
                throw "Duplicate payment found in TARGET (ID: $($dupFound[0])). Skipping."
            }

            # 9) Create payments in TARGET
            $payVals = @{
                company_id   = $selTgtComp.id
                journal_id   = $mappedTgtJournalId
                partner_id   = $tgtPartnerId
                amount       = $p.amount
                date         = $p.date
                payment_type = $p.payment_type
            }
            if ($p.partner_type) { $payVals.partner_type = $p.partner_type }
            if ($refOrComm) { $payVals.ref = $refOrComm }
            if ($tgtCurrencyId) { $payVals.currency_id = $tgtCurrencyId }
            if ($tgtPmlId) { $payVals.payment_method_line_id = $tgtPmlId }

            if ($DryRun) {
                $status = "SKIPPED"
                $reason = "DRY_RUN_SUCCESS"
                Write-Host "  -> [DRY RUN] Would create payment for Amount: $($p.amount) Date: $($p.date)" -ForegroundColor Gray
            }
            else {
                $tgtPaymentId = Invoke-OdooCreate -Conn $tgtConn -Model "account.payment" -Values $payVals
                Write-Host "  -> Created Payment in Target ID: $tgtPaymentId" -ForegroundColor Green
                
                if ($AutoPost -and $p.state -eq "posted") {
                    Invoke-OdooExecute -Conn $tgtConn -Model "account.payment" -Method "action_post" -Ids @($tgtPaymentId) | Out-Null
                    Write-Host "  -> Posted Payment in Target ID: $tgtPaymentId" -ForegroundColor Cyan
                }
                
                $status = "MIGRATED"
                $migratedIds += $p.id
                
                # Checkpoint save periodically
                if ($migratedIds.Count % 50 -eq 0) {
                    @{ migrated_ids = $migratedIds } | ConvertTo-Json | Set-Content $checkpointFile
                }
            }
            
        }
        catch {
            if ($status -eq "ERROR") {
                Write-Warning "Error processing Payment $($p.id): $_"
                $reason = $_.Exception.Message
            }
            else {
                Write-Verbose "Skipped Payment $($p.id): $_"
            }
        }
        
        $results += [PSCustomObject]@{
            SourcePaymentId       = $p.id
            SourceName            = $p.name
            SourceDate            = $p.date
            SourceAmount          = $p.amount
            SourcePartner         = Get-M2oName $p.partner_id
            SourceJournalId       = $srcJrnId
            MappedTargetJournalId = $mappedTgtJournalId
            TargetPaymentId       = $tgtPaymentId
            Status                = $status
            Reason                = $reason
            Notes                 = ""
        }
    }
    
    # Final Checkpoint save
    if (-not $DryRun) {
        @{ migrated_ids = $migratedIds } | ConvertTo-Json | Set-Content $checkpointFile
    }

    # 12) Output reports
    Write-Host "Generating Reports..." -ForegroundColor Cyan
    $timestamp = Get-Date -Format "yyyyMMdd_HHmm"
    $baseName = "PaymentMigration_${safeS}_TO_${safeT}_$timestamp"
    $csvPath = Join-Path (Resolve-Path $OutputDir).Path "$baseName.csv"
    $xlsxPath = Join-Path (Resolve-Path $OutputDir).Path "$baseName.xlsx"
    
    if ($results.Count -gt 0) {
        $results | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
        Write-Host "Exported CSV to: $csvPath" -ForegroundColor Green
        
        $summary = [PSCustomObject]@{
            SourceCompany  = $selSrcComp.name
            TargetCompany  = $selTgtComp.name
            TotalProcessed = $results.Count
            Migrated       = @($results | Where-Object { $_.Status -eq "MIGRATED" }).Count
            Skipped        = @($results | Where-Object { $_.Status -eq "SKIPPED" }).Count
            Errors         = @($results | Where-Object { $_.Status -eq "ERROR" }).Count
        }
        
        if (Get-Module -ListAvailable -Name ImportExcel) {
            $summary | Export-Excel -Path $xlsxPath -WorksheetName "Summary" -AutoSize -BoldTopRow
            
            $migrated = @($results | Where-Object { $_.Status -eq "MIGRATED" -or $_.Reason -eq "DRY_RUN_SUCCESS" })
            if ($migrated) { $migrated | Export-Excel -Path $xlsxPath -WorksheetName "Migrated" -AutoSize -BoldTopRow -TableName "Migrated" }
            
            $skipped = @($results | Where-Object { $_.Status -eq "SKIPPED" -and $_.Reason -ne "DRY_RUN_SUCCESS" })
            if ($skipped) { $skipped | Export-Excel -Path $xlsxPath -WorksheetName "Skipped" -AutoSize -BoldTopRow -TableName "Skipped" }
            
            $errors = @($results | Where-Object { $_.Status -eq "ERROR" })
            if ($errors) { $errors | Export-Excel -Path $xlsxPath -WorksheetName "Errors" -AutoSize -BoldTopRow -TableName "Errors" }
            
            Write-Host "Exported Excel report to: $xlsxPath" -ForegroundColor Green
            if ($OpenAfter) { Invoke-Item $xlsxPath }
        }
    }
    
    Write-Host "Done!" -ForegroundColor Green

}
catch {
    Write-Error "An error occurred: $_"
}

<#
HOW TO RUN:
1) Open PowerShell: powershell -ExecutionPolicy Bypass
2) Run script:
   .\migrate_payments_with_journal_mapping.ps1 `
       -PathToJournalMapCsv ".\output\journal_mapping\JournalMapping_AJMAN_TO_AJMAN_20260303_1623.csv" `
       -DryRun:$false -AutoPost:$true
3) The script will prompt for Source and Target companies, migrate matched payments, and produce comprehensive CSV/Excel reports.
#>
