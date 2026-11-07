# The scheduled prediction-ledger run (projects/prediction-ledger/BRIEF.md, decision 0017).
#
# Task Scheduler starts this at Tuesday 10:00, Thursday 12:00 and Saturday 12:00 Eastern, in a
# separate copy of the repo (a git worktree) that only ever holds the latest main from GitHub. So
# work on a branch in the main checkout can never change or block a run. It uses the main
# checkout's data folder (-DataDir), runs `pcf ledger run`, logs everything, and shows a Windows
# notice if the run fails. A run with nothing due exits quietly.
param(
    [Parameter(Mandatory = $true)][string]$DataDir
)

$ErrorActionPreference = "Stop"
$pcf = Split-Path $PSScriptRoot -Parent
$logDir = Join-Path $DataDir "logs\ledger"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir ("{0:yyyyMMdd-HHmm}.log" -f (Get-Date))

# Windows shows notices only from a registered app; PowerShell's own id is always registered.
$powershellApp = "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"

function Show-Notice([string]$text) {
    # A Windows notice with no extra modules: the built-in toast API.
    try {
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
            [Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $nodes = $xml.GetElementsByTagName("text")
        $nodes.Item(0).AppendChild($xml.CreateTextNode("PCF ledger run failed")) | Out-Null
        $nodes.Item(1).AppendChild($xml.CreateTextNode($text)) | Out-Null
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($powershellApp).Show($toast)
    } catch {
        Add-Content $log "could not show the notice: $_"
    }
}

function Step([string]$name, [scriptblock]$block) {
    # Native tools write progress and logs to stderr; in PowerShell 5.1 that mustn't count as
    # failure. Only the exit code does.
    $ErrorActionPreference = "Continue"
    Add-Content $log ("{0:s} {1}" -f (Get-Date), $name)
    $out = & $block 2>&1
    $out | ForEach-Object { Add-Content $log "$_" }
    if ($LASTEXITCODE -ne 0) { throw "$name failed (exit $LASTEXITCODE)" }
}

try {
    Step "update to the latest main" {
        git -C $pcf fetch --quiet origin main
        git -C $pcf checkout --quiet --detach origin/main
    }
    Step "sync the environment" { uv sync --frozen --project $pcf --quiet }
    $env:PCF_DATA_DIR = $DataDir
    $env:PYTHONUTF8 = "1"
    Step "pcf ledger run" { & (Join-Path $pcf ".venv\Scripts\pcf.exe") ledger run }
    Add-Content $log ("{0:s} done" -f (Get-Date))
} catch {
    Add-Content $log ("{0:s} FAILED: {1}" -f (Get-Date), $_)
    Show-Notice "$_ Log: $log"
    exit 1
}
