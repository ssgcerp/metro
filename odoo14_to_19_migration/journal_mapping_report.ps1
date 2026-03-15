<#
.SYNOPSIS
    Odoo Journal Mapping Report

.DESCRIPTION
    Creates an interactive mapping tool that compares Journals between a SOURCE database and a TARGET database.
    Produces an Excel report identifying matched, missing, duplicates, and suggested mapping.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\journal_mapping_report.ps1 -OpenAfter -UseEnvCreds
#>

[CmdletBinding()]
param (
    [string]$OutputDir = ".\output\journal_mapping\",
    [switch]$OpenAfter,
    [switch]$UseEnvCreds
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
                # Could be a single node or an array of .value nodes
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
        # Using a custom property to display ID clearly without breaking the original object binding
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
    
    # In case array returned (e.g., user selected multiple in Out-GridView by mistake), take first
    if ($selected -is [array]) { $selected = $selected[0] }
    return $selected
}

# ---------------------------------------------------------
# UTILS & HELPERS
# ---------------------------------------------------------

function Get-M2oName {
    param($Field)
    if ($null -eq $Field) { return "" }
    if ($Field -is [array] -and $Field.Count -eq 2) { return "$($Field[1])" }
    return ""
}

function Get-Similarity {
    param([string]$str1, [string]$str2)
    if ([string]::IsNullOrWhiteSpace($str1) -or [string]::IsNullOrWhiteSpace($str2)) { return 0 }
    $s1 = $str1.ToLower().Trim()
    $s2 = $str2.ToLower().Trim()
    if ($s1 -eq $s2) { return 100 }
    if ($s1.Contains($s2) -or $s2.Contains($s1)) { return 80 }
    
    $words1 = $s1 -split '\s+'
    $words2 = $s2 -split '\s+'
    $common = ($words1 | Where-Object { $words2 -contains $_ }).Count
    $max = [Math]::Max($words1.Count, $words2.Count)
    if ($max -eq 0) { return 0 }
    return [Math]::Round(($common / $max) * 50) 
}

# Wrapper to safely fetch journals whether running on Odoo 14 or 19
function Fetch-JournalsSafe {
    param($Conn, $Domain)
    $requestedFields = @("id", "name", "code", "type", "company_id", "active", "currency_id", "default_account_id", "suspense_account_id", "profit_account_id", "loss_account_id", "refund_sequence", "sequence_id", "inbound_payment_method_line_ids", "outbound_payment_method_line_ids")
    
    # Dynamically verify which fields exist in this Odoo version
    $availableFields = Get-OdooFields -Conn $Conn -Model "account.journal"
    $realFields = @()
    foreach ($f in $requestedFields) {
        if ($availableFields.ContainsKey($f)) {
            $realFields += $f
        }
    }
    
    return Invoke-OdooSearchRead -Conn $Conn -Model "account.journal" -Domain $Domain -Fields $realFields
}

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------

try {
    Write-Host "========== ODOO JOURNAL MAPPING TOOL ==========" -ForegroundColor White -BackgroundColor DarkBlue

    # Connect to Source
    $srcConn = Connect-Odoo -Url $URL_SRC -Db $DB_SRC -User $USER_SRC -Pass $PASS_SRC
    # Connect to Target
    $tgtConn = Connect-Odoo -Url $URL_TGT -Db $DB_TGT -User $USER_TGT -Pass $PASS_TGT
    
    Write-Host "Fetching companies..." -ForegroundColor Cyan
    $srcCompanies = Invoke-OdooSearchRead -Conn $srcConn -Model "res.company" -Domain @() -Fields @("id", "name")
    $tgtCompanies = Invoke-OdooSearchRead -Conn $tgtConn -Model "res.company" -Domain @() -Fields @("id", "name")
    
    $selSrcComp = Select-Company -Title "Select SOURCE Company ($DB_SRC)" -Companies $srcCompanies
    Write-Host "Selected Source Company: $($selSrcComp.name)" -ForegroundColor Green
    
    $selTgtComp = Select-Company -Title "Select TARGET Company/Branch ($DB_TGT)" -Companies $tgtCompanies
    Write-Host "Selected Target Company: $($selTgtComp.name)" -ForegroundColor Green

    # ---------------------------------------------------------
    # 3) DATA EXTRACTION (Journals)
    # ---------------------------------------------------------
    Write-Host "Fetching Journals for the selected companies..." -ForegroundColor Cyan
    $domain_src = @( , @("company_id", "=", $selSrcComp.id) )
    $domain_tgt = @( , @("company_id", "=", $selTgtComp.id) )
    
    $srcJournals = Fetch-JournalsSafe -Conn $srcConn -Domain $domain_src
    $tgtJournals = Fetch-JournalsSafe -Conn $tgtConn -Domain $domain_tgt
    
    Write-Host "Found $($srcJournals.Count) journals in Source, $($tgtJournals.Count) journals in Target."

    # ---------------------------------------------------------
    # 4) MATCHING LOGIC (Mapping)
    # ---------------------------------------------------------
    Write-Host "Analyzing & Matching Journals..." -ForegroundColor Cyan
    
    $srcCodeCounts = @{}
    if ($srcJournals) {
        $srcJournals | ForEach-Object { $c = "$($_.code)".ToLower().Trim(); $srcCodeCounts[$c]++ }
    }
    
    $tgtCodeCounts = @{}
    if ($tgtJournals) {
        $tgtJournals | ForEach-Object { $c = "$($_.code)".ToLower().Trim(); $tgtCodeCounts[$c]++ }
    }

    $mappingList = @()
    $mappedTgtIds = @()
    
    if ($srcJournals) {
        foreach ($s in $srcJournals) {
            $sCode = "$($s.code)".ToLower().Trim()
            $sName = "$($s.name)".ToLower().Trim()
            
            $matchTgt = $null
            $rule = "NONE"
            $score = 0
            
            # Primary: Exact Code Match
            $matchCode = @($tgtJournals | Where-Object { "$($_.code)".ToLower().Trim() -eq $sCode })
            if ($matchCode.Count -gt 0) {
                $matchTgt = $matchCode
                $rule = "CODE"
                $score = 100
            }
            else {
                # Secondary: Exact Name Match
                $matchName = @($tgtJournals | Where-Object { "$($_.name)".ToLower().Trim() -eq $sName })
                if ($matchName.Count -gt 0) {
                    $matchTgt = $matchName
                    $rule = "NAME"
                    $score = 100
                }
                else {
                    # Tertiary: Fuzzy Score
                    $bestTgt = $null
                    $bestScore = 0
                    foreach ($t in $tgtJournals) {
                        $sim = Get-Similarity $sName "$($t.name)"
                        if ($sim -gt $bestScore) {
                            $bestScore = $sim
                            $bestTgt = $t
                        }
                    }
                    if ($bestScore -ge 50) {
                        $matchTgt = @($bestTgt)
                        $rule = "FUZZY"
                        $score = $bestScore
                    }
                }
            }
            
            $status = "MISSING_IN_TARGET"
            $selMatchTgt = $null
            if ($matchTgt) {
                if ($matchTgt.Count -gt 1) {
                    $selMatchTgt = $matchTgt[0]
                    $status = "AMBIGUOUS"
                }
                else {
                    $selMatchTgt = $matchTgt[0]
                    $status = "MATCHED"
                }
                $mappedTgtIds += $selMatchTgt.id
            }
            
            # Duplicate flags
            $notes = ""
            if ($srcCodeCounts[$sCode] -gt 1) { $notes += "Duplicate code in Source. " }
            
            if ($selMatchTgt) {
                $tgtCode = "$($selMatchTgt.code)".ToLower().Trim()
                if ($tgtCodeCounts[$tgtCode] -gt 1) { $notes += "Duplicate code in Target. " }
            }
            if ($status -eq "AMBIGUOUS") {
                $notes += "Multiple targets matched ($($matchTgt.Count) found). Checked first one. "
            }
            
            $mappingList += [PSCustomObject]@{
                SourceJournalId      = $s.id
                SourceJournalName    = $s.name
                SourceJournalCode    = $s.code
                SourceType           = $s.type
                SourceActive         = $s.active
                SourceDefaultAccount = (Get-M2oName $s.default_account_id)
                TargetJournalId      = if ($selMatchTgt) { $selMatchTgt.id } else { $null }
                TargetJournalName    = if ($selMatchTgt) { $selMatchTgt.name } else { "" }
                TargetJournalCode    = if ($selMatchTgt) { $selMatchTgt.code } else { "" }
                TargetType           = if ($selMatchTgt) { $selMatchTgt.type } else { "" }
                TargetActive         = if ($selMatchTgt) { $selMatchTgt.active } else { $null }
                MatchRuleUsed        = $rule
                MatchScore           = $score
                MappingStatus        = $status
                Notes_Suggestions    = $notes.Trim()
            }
        }
    }
    
    # Target-Only Journals
    $targetOnlyList = @()
    if ($tgtJournals) {
        foreach ($t in $tgtJournals) {
            if ($mappedTgtIds -notcontains $t.id) {
                $targetOnlyList += [PSCustomObject]@{
                    TargetJournalId      = $t.id
                    TargetJournalName    = $t.name
                    TargetJournalCode    = $t.code
                    TargetType           = $t.type
                    TargetActive         = $t.active
                    TargetDefaultAccount = (Get-M2oName $t.default_account_id)
                }
            }
        }
    }
    
    # ---------------------------------------------------------
    # 5) EXCEL REPORT EXPORT
    # ---------------------------------------------------------
    Write-Host "Generating Reports..." -ForegroundColor Cyan
    
    if (!(Test-Path $OutputDir)) { 
        New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null 
    }
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmm"
    $safeS = $selSrcComp.name -replace '[^a-zA-Z0-9]', '_'
    $safeT = $selTgtComp.name -replace '[^a-zA-Z0-9]', '_'
    $baseName = "JournalMapping_${safeS}_TO_${safeT}_$timestamp"
    $xlsxPath = Join-Path (Resolve-Path $OutputDir).Path "$baseName.xlsx"
    $csvPath = Join-Path (Resolve-Path $OutputDir).Path "$baseName.csv"
    
    if ($mappingList.Count -gt 0) {
        $mappingList | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
        Write-Host "Exported mapping CSV to: $csvPath" -ForegroundColor Green
    }
    
    $summary = [PSCustomObject]@{
        SourceCompany       = $selSrcComp.name
        TargetCompany       = $selTgtComp.name
        TotalSourceJournals = if ($srcJournals) { $srcJournals.Count } else { 0 }
        Matched             = @($mappingList | Where-Object { $_.MappingStatus -eq "MATCHED" }).Count
        MissingTarget       = @($mappingList | Where-Object { $_.MappingStatus -eq "MISSING_IN_TARGET" }).Count
        Ambiguous           = @($mappingList | Where-Object { $_.MappingStatus -eq "AMBIGUOUS" }).Count
        TargetOnly          = $targetOnlyList.Count
    }
    
    # Check Install-Module ImportExcel
    if (-not (Get-Module -ListAvailable -Name ImportExcel)) {
        Write-Host "The 'ImportExcel' module is required to generate the .xlsx report." -ForegroundColor Yellow
        $installChoice = Read-Host "Would you like to install 'ImportExcel' now for the CurrentUser? (Y/N)"
        if ($installChoice -match "^[yY]") {
            Write-Host "Installing ImportExcel module..." -ForegroundColor Cyan
            Install-Module ImportExcel -Scope CurrentUser -Force
            # Make it available in current session
            Import-Module ImportExcel
        }
        else {
            Write-Warning "Skipping Excel generation. Check the CSV output instead."
        }
    }
    
    if (Get-Module -ListAvailable -Name ImportExcel) {
        $summary | Export-Excel -Path $xlsxPath -WorksheetName "Summary" -AutoSize -BoldTopRow
        
        if ($srcJournals) {
            $srcJournals | Select-Object id, name, code, type, active, 
            @{N = 'default_account'; E = { Get-M2oName $_.default_account_id } }, 
            @{N = 'currency'; E = { Get-M2oName $_.currency_id } } |
            Export-Excel -Path $xlsxPath -WorksheetName "Source_Journals" -AutoSize -BoldTopRow -TableName "SrcGroup"
        }
        
        if ($tgtJournals) {
            $tgtJournals | Select-Object id, name, code, type, active, 
            @{N = 'default_account'; E = { Get-M2oName $_.default_account_id } }, 
            @{N = 'currency'; E = { Get-M2oName $_.currency_id } } |
            Export-Excel -Path $xlsxPath -WorksheetName "Target_Journals" -AutoSize -BoldTopRow -TableName "TgtGroup"
        }
        
        if ($mappingList) {
            $mappingList | Export-Excel -Path $xlsxPath -WorksheetName "Mapping" -AutoSize -BoldTopRow -TableName "Mapping" -AutoFilter
        }
        
        if ($targetOnlyList.Count -gt 0) {
            $targetOnlyList | Export-Excel -Path $xlsxPath -WorksheetName "Target_Only" -AutoSize -BoldTopRow -TableName "TgtOnly"
        }
        
        Write-Host "Exported Excel report to: $xlsxPath" -ForegroundColor Green
        
        if ($OpenAfter) {
            Invoke-Item $xlsxPath
        }
    }
    
    Write-Host "Done!" -ForegroundColor Green

}
catch {
    Write-Error "An error occurred: $_"
}
