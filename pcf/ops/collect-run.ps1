# The collectors, run from this PC while GitHub Actions is locked (live-experts brief, decision 3A,
# the CEO, 2026-11-10). It does what .github/workflows/collect-odds.yml and snapshot-nflverse.yml
# do, with the same scripts, and pushes to the same private pcf-data repo.
#
#   -What odds      ESPN lines and props, then The Odds API (the key is read from pcf/.env in the
#                   main checkout and never written to the log)
#   -What nflverse  the daily nflverse snapshot (`pcf refresh --snapshots-only`)
#
# It works in its own clone of pcf-data (<DataDir>/collect/pcf-data), not the ledger's sparse one.
# If GitHub's own collector has pushed in the last 2 days, Actions is running again: it collects
# nothing, so The Odds API's credits aren't spent twice, and shows a notice to remove these tasks.
# Task Scheduler starts it in the live copy of the repo (the latest main); a failure shows a
# Windows notice, as the ledger run does.
param(
    [Parameter(Mandatory = $true)][ValidateSet("odds", "nflverse")][string]$What,
    [Parameter(Mandatory = $true)][string]$DataDir
)

$ErrorActionPreference = "Stop"
$pcf = Split-Path $PSScriptRoot -Parent
$python = Join-Path $pcf ".venv\Scripts\python.exe"
$clone = Join-Path $DataDir "collect\pcf-data"
$logDir = Join-Path $DataDir "logs\collect"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir ("{0}-{1:yyyyMMdd-HHmm}.log" -f $What, (Get-Date))
$powershellApp = "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"

function Show-Notice([string]$title, [string]$text) {
    try {
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
            [Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $nodes = $xml.GetElementsByTagName("text")
        $nodes.Item(0).AppendChild($xml.CreateTextNode($title)) | Out-Null
        $nodes.Item(1).AppendChild($xml.CreateTextNode($text)) | Out-Null
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($powershellApp).Show($toast)
    } catch {
        Add-Content $log "could not show the notice: $_"
    }
}

function Step([string]$name, [scriptblock]$block) {
    # Native tools write progress to stderr; in PowerShell 5.1 only the exit code means failure.
    $ErrorActionPreference = "Continue"
    Add-Content $log ("{0:s} {1}" -f (Get-Date), $name)
    $out = & $block 2>&1
    $out | ForEach-Object { Add-Content $log "$_" }
    if ($LASTEXITCODE -ne 0) { throw "$name failed (exit $LASTEXITCODE)" }
}

try {
    if (-not (Test-Path (Join-Path $clone ".git"))) {
        Step "clone pcf-data" { git clone --quiet https://github.com/jackdepree/pcf-data.git $clone }
    }
    Step "update pcf-data" { git -C $clone pull --quiet --rebase }

    # GitHub's collector commits as exactly "pcf-collector"; this script as "pcf-collector-pc".
    $actions = git -C $clone log --since="2 days ago" --author="^pcf-collector <" --format=%h
    if ($actions) {
        Add-Content $log ("{0:s} GitHub Actions collected recently ({1}): nothing to do" -f (Get-Date), ($actions -join " "))
        Show-Notice "PCF collectors: GitHub is back" "Actions is collecting again. Remove the PC tasks: powershell -File pcf\ops\register-collector-tasks.ps1 -Remove"
        exit 0
    }

    $env:PCF_DATA_DIR = $clone
    $env:PYTHONUTF8 = "1"
    $explore = Join-Path $pcf "projects\odds-collection\explore"
    if ($What -eq "odds") {
        # The key lives in the main checkout's pcf/.env (rule g). Read, never printed.
        $envFile = Join-Path (Split-Path $DataDir -Parent) ".env"
        $line = Get-Content $envFile -ErrorAction SilentlyContinue | Where-Object { $_ -match '^\s*ODDS_API_KEY\s*=' } | Select-Object -First 1
        if ($line) { $env:ODDS_API_KEY = ($line -split "=", 2)[1].Trim().Trim('"').Trim("'") }
        Step "ESPN lines and props" { & $python (Join-Path $explore "backfill_espn.py") --current-season }
        Step "The Odds API lines and props" { & $python (Join-Path $explore "collect_odds_api.py") }
        Remove-Item Env:\ODDS_API_KEY -ErrorAction SilentlyContinue
        $paths = @("raw/espn_odds", "raw/odds_api")
    } else {
        # nflverse sometimes replaces a file mid-download (its fingerprint no longer matches): one
        # retry a minute later, as the ledger's own pull does.
        try {
            Step "nflverse snapshot" { & $python -m pcf.cli refresh --snapshots-only }
        } catch {
            Add-Content $log ("{0:s} {1}; trying again in 60 seconds" -f (Get-Date), $_)
            Start-Sleep -Seconds 60
            Step "nflverse snapshot, again" { & $python -m pcf.cli refresh --snapshots-only }
        }
        $paths = @("raw/nflverse")
    }

    Step "save to pcf-data" {
        git -C $clone add -- $paths
        git -C $clone diff --cached --quiet
        if ($LASTEXITCODE -eq 0) {
            "nothing new"
            $global:LASTEXITCODE = 0
        } else {
            $stamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mmZ")
            git -C $clone -c user.name="pcf-collector-pc" -c user.email="pcf-collector@users.noreply.github.com" commit --quiet -m "$What snapshot $stamp (from the PC; Actions locked)"
            git -C $clone pull --quiet --rebase
            git -C $clone push --quiet
        }
    }
    Add-Content $log ("{0:s} done" -f (Get-Date))
} catch {
    Add-Content $log ("{0:s} FAILED: {1}" -f (Get-Date), $_)
    Show-Notice "PCF $What collector failed" "$_ Log: $log"
    exit 1
}
