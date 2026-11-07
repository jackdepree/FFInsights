# Sets up the scheduled prediction-ledger run, once (decision 0017). Needs the CEO's approval.
#
# 1. Makes a separate copy of the repo next to this one (`FFInsights-live`, a git worktree) that
#    only ever holds the latest main from GitHub, with its own Python environment.
# 2. Registers one Windows task, "PCF ledger run", for Tuesday 10:00, Thursday 12:00 and Saturday
#    12:00 local time (this PC is on Eastern). It wakes the PC, runs as soon as it can if a time
#    was missed, and runs only while the CEO is logged in, so no Windows password is stored.
#
# Run from anywhere: powershell -ExecutionPolicy Bypass -File pcf\ops\register-ledger-task.ps1
# To remove it later: Unregister-ScheduledTask -TaskName "PCF ledger run"
# Safe to run again: it updates the copy to the latest main and replaces the task.
param(
    # The first day the schedule may run (default: tomorrow), so it can't clash with a test run.
    [datetime]$StartDate = (Get-Date).Date.AddDays(1)
)
$ErrorActionPreference = "Stop"
$pcf = Split-Path $PSScriptRoot -Parent
$repo = Split-Path $pcf -Parent
$live = Join-Path (Split-Path $repo -Parent) "FFInsights-live"
$dataDir = Join-Path $pcf "data"

git -C $repo fetch --quiet origin main
if (-not (Test-Path $live)) {
    git -C $repo worktree add --detach $live origin/main
    if ($LASTEXITCODE -ne 0) { throw "could not make the worktree" }
}
git -C $live checkout --quiet --detach origin/main
if ($LASTEXITCODE -ne 0) { throw "could not update the worktree" }
uv sync --frozen --project (Join-Path $live "pcf")
if ($LASTEXITCODE -ne 0) { throw "could not set up its environment" }

$script = Join-Path $live "pcf\ops\ledger-run.ps1"
if (-not (Test-Path $script)) {
    Write-Warning "main doesn't have the ledger yet: merge it, then run this script again"
}
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`" -DataDir `"$dataDir`""
$triggers = @(
    New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday -At $StartDate.AddHours(10)
    New-ScheduledTaskTrigger -Weekly -DaysOfWeek Thursday -At $StartDate.AddHours(12)
    New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday -At $StartDate.AddHours(12)
)
$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
Register-ScheduledTask -TaskName "PCF ledger run" -Force -Action $action -Trigger $triggers `
    -Settings $settings -Principal $principal `
    -Description "Forecasts due games and pushes them to the private pcf-data repo (PCF prediction ledger)." | Out-Null
Get-ScheduledTask -TaskName "PCF ledger run" | Get-ScheduledTaskInfo | Select-Object TaskName, NextRunTime
