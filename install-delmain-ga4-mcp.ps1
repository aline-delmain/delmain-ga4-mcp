#requires -Version 5.1
<#
.SYNOPSIS
  One-shot installer for the :Delmain GA4 MCP server (Windows).

.DESCRIPTION
  Run this and you're done. It:
    1. Finds your Python 3.
    2. Installs the package from GitHub (uses `python -m pip`, so a bare
       `pip` on PATH is not required).
    3. Locates the installed executable and registers the MCP server with
       Claude Code using its FULL path (works even when Python's Scripts
       folder is not on PATH).
    4. Prepares ~/.delmain-ga4-mcp/.env and asks for the OAuth client
       credentials (from the team vault) if they are not set yet.
    5. Runs the Google authorization in your browser.

.PARAMETER SkipSetup
  Skip the browser OAuth step (step 5).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\install-delmain-ga4-mcp.ps1
#>

[CmdletBinding()]
param(
    [string]$Repo = "https://github.com/aline-delmain/delmain-ga4-mcp.git",
    [switch]$SkipSetup
)

$ErrorActionPreference = "Stop"

function Step($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "    $m" -ForegroundColor Green }
function Note($m) { Write-Host "    $m" -ForegroundColor Yellow }

# --- 1. Find Python 3 -------------------------------------------------------
Step "Looking for Python 3..."
$py = $null
foreach ($cand in @(, @("python"), @("py", "-3"), @("python3"))) {
    $exe = $cand[0]
    if (Get-Command $exe -ErrorAction SilentlyContinue) {
        $pre = @($cand | Select-Object -Skip 1)
        try {
            $v = & $exe @pre "--version" 2>&1
            if ($LASTEXITCODE -eq 0 -and "$v" -match "Python 3") { $py = $cand; break }
        } catch {}
    }
}
if (-not $py) {
    throw "Python 3 not found. Install from https://www.python.org/downloads/ (tick 'Add python.exe to PATH') and re-run."
}
$pyExe = $py[0]
$pyPre = @($py | Select-Object -Skip 1)
function Py { param([Parameter(ValueFromRemainingArguments = $true)]$a) & $pyExe @pyPre @a }
Ok ("Using: " + ($py -join ' '))

# --- 2. Install the package -------------------------------------------------
Step "Installing delmain-ga4-mcp from GitHub..."
Py -m pip install --upgrade "git+$Repo"
if ($LASTEXITCODE -ne 0) { throw "pip install failed (is git installed?)." }
Ok "Package installed."

# --- 3. Locate the executable and register with Claude Code -----------------
Step "Locating the installed executable..."
$dirs = (Py -c "import sysconfig,site,os;print(sysconfig.get_path('scripts'));print(os.path.join(site.getuserbase(),'Scripts'))") -split "`r?`n" | Where-Object { $_ }
$serverExe = $null
foreach ($d in $dirs) {
    $p = Join-Path $d.Trim() "delmain-ga4-mcp.exe"
    if (Test-Path $p) { $serverExe = $p; break }
}
if (-not $serverExe) { throw "Could not find delmain-ga4-mcp.exe after install. Searched: $($dirs -join '; ')" }
Ok "Found: $serverExe"

Step "Registering the MCP server with Claude Code..."
$registered = $false
if (Get-Command claude -ErrorAction SilentlyContinue) {
    try { & claude mcp remove delmain-ga4 --scope user 2>$null | Out-Null } catch {}
    & claude mcp add delmain-ga4 --scope user -- "$serverExe"
    if ($LASTEXITCODE -eq 0) { Ok "Registered as 'delmain-ga4' (user scope)."; $registered = $true }
}
if (-not $registered) {
    Note "Couldn't auto-register (no 'claude' CLI, or you use Claude Desktop)."
    Note "Add this to your MCP client config manually:"
    $jsonPath = $serverExe.Replace('\', '\\')
    Write-Host ""
    Write-Host "      `"mcpServers`": {"
    Write-Host "        `"delmain-ga4`": { `"command`": `"$jsonPath`" }"
    Write-Host "      }"
    Write-Host ""
}

# --- 4. Prepare the per-user .env ------------------------------------------
Step "Preparing your credentials file..."
$cfgDir = Join-Path $env:USERPROFILE ".delmain-ga4-mcp"
New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null
$envPath = Join-Path $cfgDir ".env"

$existing = @{}
if (Test-Path $envPath) {
    foreach ($line in Get-Content $envPath) {
        if ($line.TrimStart().StartsWith("#")) { continue }
        if ($line -match '^\s*([A-Z0-9_]+)\s*=\s*"?(.*?)"?\s*$') { $existing[$matches[1]] = $matches[2] }
    }
}

function Resolve-Value($key, $prompt) {
    if ($existing[$key]) { Ok "$key already set."; return $existing[$key] }
    return (Read-Host $prompt)
}

$cid  = Resolve-Value "DELMAIN_GA4_CLIENT_ID"     "Paste DELMAIN_GA4_CLIENT_ID (from the team vault)"
$csec = Resolve-Value "DELMAIN_GA4_CLIENT_SECRET" "Paste DELMAIN_GA4_CLIENT_SECRET (from the team vault)"
$rtok = if ($existing["DELMAIN_GA4_REFRESH_TOKEN"]) { $existing["DELMAIN_GA4_REFRESH_TOKEN"] } else { "" }

@"
DELMAIN_GA4_CLIENT_ID="$cid"
DELMAIN_GA4_CLIENT_SECRET="$csec"
DELMAIN_GA4_REFRESH_TOKEN="$rtok"
"@ | Set-Content -Path $envPath -Encoding utf8
Ok "Wrote $envPath"

# --- 5. Authorize with Google ----------------------------------------------
if ($SkipSetup) {
    Note "Skipping OAuth (-SkipSetup). Run 'delmain-ga4-mcp-setup' later to authorize."
} elseif ($rtok) {
    Ok "Refresh token already present, skipping OAuth."
} else {
    Step "Authorizing with Google (opens your browser)..."
    $setupExe = Join-Path (Split-Path $serverExe) "delmain-ga4-mcp-setup.exe"
    if (Test-Path $setupExe) { & $setupExe } else { Py -m delmain_ga4_mcp.setup_cli }
}

Step "Done."
Ok "Restart your MCP client (Claude Code / Desktop / Cursor) to load the GA4 tools."
