# Needs ExchangeOnlineManagement. (#Requires removed 2026-10-20: the .psd1 load hangs on ExoMac's portable pwsh;
# the module is imported via its netCore .psm1 below when not already loaded.)
<#
.SYNOPSIS
    Deploys the Exos canonical blocked-senders list as a company-wide
    Exchange Online transport rule on the M365 GCC High tenant.

.DESCRIPTION
    Reads Blocked_Senders_Current.txt (same file peaton's Outlook updater uses),
    then creates or replaces an Exchange Online mail-flow rule named
    "Exos DD-Blocked Senders" that applies to ALL inbound messages org-wide.

    Matching messages are rejected with a 550 NDR (sender gets a bounce).
    Set $Action = "Quarantine" if you prefer silent discard to Quarantine instead.

    IMPORTANT: This is a GCC High tenant (.us endpoints).
    Connect with: Connect-ExchangeOnline -ExchangeEnvironmentName O365USGovGCCHigh

    Run as a Global Admin or Exchange Admin on a Windows machine with
    the ExchangeOnlineManagement module installed.

.PARAMETER BlockListPath
    Path to the TXT block-list file. Defaults to Blocked_Senders_Current.txt
    in the same folder as this script.

.PARAMETER WhatIf
    Show what would change without actually applying anything.

.EXAMPLE
    .\Deploy-Exos-Blocked-Senders-Tenant.ps1
    .\Deploy-Exos-Blocked-Senders-Tenant.ps1 -WhatIf
    .\Deploy-Exos-Blocked-Senders-Tenant.ps1 -BlockListPath "C:\path\to\updated.txt"
#>

param(
    [string]$BlockListPath = "$PSScriptRoot\Blocked_Senders_Current.txt",
    [ValidateSet('Quarantine','Reject')]
    [string]$Action = 'Quarantine',          # Phil 2026-10-20: send to Microsoft hosted quarantine, not bounce
    [string[]]$StrictUsers = @(),            # mailboxes to add to the Strict preset (spam/bulk -> quarantine, not Junk)
    [switch]$Device,                         # device-code sign-in (ExoMac / non-Windows)
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
$RuleName = 'Exos DD-Blocked Senders'

Write-Host ''
Write-Host 'EXOS COMPANY-WIDE BLOCKED-SENDERS — TENANT RULE DEPLOYER' -ForegroundColor Green
Write-Host 'Target: M365 GCC High — all inbound messages, all mailboxes'
Write-Host ''

# --- Load + parse block list (same parser logic as the Outlook PS1) ----------
if (-not (Test-Path $BlockListPath)) {
    throw "Block-list file not found: $BlockListPath"
}

$domains  = [System.Collections.Generic.List[string]]::new()
$emails   = [System.Collections.Generic.List[string]]::new()
$lineNum  = 0

foreach ($line in Get-Content -LiteralPath $BlockListPath) {
    $lineNum++
    $entry = $line.Trim()
    if ($entry.Length -eq 0 -or $entry.StartsWith('#')) { continue }

    if ($entry.StartsWith('*@')) { $entry = $entry.Substring(2) }
    elseif ($entry.StartsWith('@')) { $entry = $entry.Substring(1) }

    if ($entry -match '\s') {
        Write-Warning "Skipping invalid entry on line $lineNum : $line"
        continue
    }

    # Distinguish full email address vs bare domain
    if ($entry -match '^[^@]+@[^@]+$') {
        $emails.Add($entry.ToLower())
    } else {
        $domains.Add($entry.ToLower())
    }
}

$domains = @($domains | Sort-Object -Unique)
$emails  = @($emails  | Sort-Object -Unique)
$total   = $domains.Count + $emails.Count

if ($total -eq 0) { throw "No usable entries found in: $BlockListPath" }

Write-Host "Block-list loaded: $($domains.Count) domains, $($emails.Count) full addresses ($total total)"
Write-Host ''

if ($WhatIf) {
    Write-Host '[WHATIF] Would create/replace transport rule:' -ForegroundColor Yellow
    Write-Host "  Rule name : $RuleName"
    Write-Host "  Scope     : all inbound (FromScope = NotInOrganization)"
    Write-Host "  Condition : SenderDomainIs OR From list"
    Write-Host "  Action    : $Action"
    if ($StrictUsers.Count) { Write-Host "  Strict preset (spam/bulk -> quarantine) for: $($StrictUsers -join ', ')" }
    Write-Host "  Priority  : 0 (highest)"
    Write-Host ''
    Write-Host '[WHATIF] Domains to block:' -ForegroundColor Yellow
    $domains | ForEach-Object { Write-Host "  $_" }
    if ($emails.Count -gt 0) {
        Write-Host '[WHATIF] Full addresses to block:' -ForegroundColor Yellow
        $emails | ForEach-Object { Write-Host "  $_" }
    }
    Write-Host ''
    Write-Host 'No changes were made (WhatIf mode).' -ForegroundColor Yellow
    exit 0
}

# --- Connect to GCC High Exchange Online -------------------------------------
if (-not (Get-Module ExchangeOnlineManagement)) {   # Get-Command would autoload the hanging .psd1
    $exo = Get-ChildItem "$HOME/.local/share/powershell/Modules/ExchangeOnlineManagement/*/netCore/ExchangeOnlineManagement.psm1" -ErrorAction SilentlyContinue | Select-Object -Last 1
    if ($exo) { Import-Module $exo.FullName } else { Import-Module ExchangeOnlineManagement }
}
Write-Host 'Connecting to Exchange Online (GCC High)...' -ForegroundColor Cyan
if ($Device) {
    Connect-ExchangeOnline -ExchangeEnvironmentName O365USGovGCCHigh -Device -ShowBanner:$false
} else {
    Connect-ExchangeOnline -ExchangeEnvironmentName O365USGovGCCHigh -ShowBanner:$false
}
Write-Host 'Connected.' -ForegroundColor Green
Write-Host ''

# --- Remove existing rule with the same name (safe to re-run) ----------------
# Match the base name AND the '(domains)' / '(addresses)' split rules created below.
$existing = Get-TransportRule | Where-Object { $_.Name -like "$RuleName*" }
foreach ($r in $existing) {
    Write-Host "Removing existing rule '$($r.Name)'..." -ForegroundColor Yellow
    Remove-TransportRule -Identity $r.Identity -Confirm:$false
}

# --- Build condition hash (domains and/or full addresses) --------------------
$ruleParams = @{
    Name                          = $RuleName
    Priority                      = 0
    Enabled                       = $true
    StopRuleProcessing            = $true
    FromScope                     = 'NotInOrganization'   # inbound from outside Exos (was SentToScope=NotInOrganization, which only matched OUTBOUND mail - fixed 2026-09-27)
}
if ($Action -eq 'Quarantine') {
    $ruleParams['Quarantine'] = $true        # Microsoft 365: delivered to the hosted quarantine
} else {
    $ruleParams['RejectMessageEnhancedStatusCode'] = '5.7.1'
    $ruleParams['RejectMessageReasonText']         = 'Message rejected. Sender is on the Exos denied-party block list.'
}

# Transport rules need at least one condition. We use SenderDomainIs for
# domains and From for specific addresses. If both lists are non-empty we
# create two rules and chain them; if only one type exists, one rule suffices.

if ($domains.Count -gt 0 -and $emails.Count -eq 0) {
    $ruleParams['SenderDomainIs'] = $domains
    New-TransportRule @ruleParams | Out-Null
}
elseif ($emails.Count -gt 0 -and $domains.Count -eq 0) {
    $ruleParams['From'] = $emails
    New-TransportRule @ruleParams | Out-Null
}
else {
    # Both — create two rules under the same banner name (suffix them)
    $domainParams = $ruleParams.Clone()
    $domainParams['Name']            = "$RuleName (domains)"
    $domainParams['SenderDomainIs']  = $domains
    New-TransportRule @domainParams | Out-Null

    $emailParams  = $ruleParams.Clone()
    $emailParams['Name']   = "$RuleName (addresses)"
    $emailParams['From']   = $emails
    $emailParams['Priority'] = 1
    New-TransportRule @emailParams | Out-Null
}

# --- Optional: put named mailboxes in the Strict preset (spam + bulk -> quarantine) ---
if ($StrictUsers.Count -gt 0) {
    $strict = Get-EOPProtectionPolicyRule -Identity 'Strict Preset Security Policy' -ErrorAction SilentlyContinue
    if (-not $strict) {
        Write-Warning 'Strict preset is not turned on in this tenant (rule missing). Turn on Strict protection once at https://security.microsoft.us/presetSecurityPolicies, then re-run with -StrictUsers.'
    } else {
        $sentTo = @($strict.SentTo) + $StrictUsers | Where-Object { $_ } | Sort-Object -Unique
        Set-EOPProtectionPolicyRule -Identity 'Strict Preset Security Policy' -SentTo $sentTo
        if ($strict.State -ne 'Enabled') { Enable-EOPProtectionPolicyRule -Identity 'Strict Preset Security Policy' }
        Write-Host "Strict preset now applies to: $($sentTo -join ', ')" -ForegroundColor Green
    }
}

# --- Verify ------------------------------------------------------------------
Write-Host ''
Write-Host 'Verifying...' -ForegroundColor Cyan
$created = Get-TransportRule | Where-Object { $_.Name -like "$RuleName*" }
if (-not $created) {
    throw "Verification failed — rule not found after creation."
}

Write-Host ''
Write-Host "SUCCESS: '$RuleName' is live on the tenant." -ForegroundColor Green
foreach ($r in $created) {
    Write-Host "  Rule: $($r.Name)  |  Priority: $($r.Priority)  |  Enabled: $($r.Enabled)"
}
Write-Host ''
Write-Host "All inbound messages from $total blocked senders: $Action."

Write-Host 'Review in EAC: https://admin.exchange.microsoft.us -> Mail flow -> Rules'
Write-Host ''
Write-Host 'Disconnecting...'
Disconnect-ExchangeOnline -Confirm:$false
