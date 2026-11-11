# Sets up the collectors on this PC while GitHub Actions is locked (live-experts brief, decision 3A,
# approved by the CEO on 2026-11-10). Two Windows tasks, at the times of the Actions schedules
# (this PC is on Eastern), each running pcf\ops\collect-run.ps1 in the live copy of the repo that
# the ledger task keeps on the latest main:
#
#   "PCF odds (PC)"      Tue 10:30, Thu 15:00, Sat 10:30, Sun 07:00, Mon 15:00
#                        (Actions: Tue 15:00, Thu 20:00, Sat 15:00, Sun 12:00, Mon 20:00 UTC;
#                        Tuesday and Saturday move 30 minutes so they don't start with the ledger)
#   "PCF nflverse (PC)"  daily 08:30 (Actions: 13:00 UTC)
#
# They wake the PC, run as soon as they can after a missed time, and only while the CEO is logged
# in, so no Windows password is stored. Once GitHub's own collectors run again, collect-run.ps1
# stops collecting and says so; then remove the tasks:
#
#   powershell -ExecutionPolicy Bypass -File pcf\ops\register-collector-tasks.ps1 -Remove
#
# Run from anywhere: powershell -ExecutionPolicy Bypass -File pcf\ops\register-collector-tasks.ps1
param(
    [switch]$Remove,
    [datetime]$StartDate = (Get-Date).Date.AddDays(1)
)
$ErrorActionPreference = "Stop"
$names = @("PCF odds (PC)", "PCF nflverse (PC)")
if ($Remove) {
    foreach ($n in $names) { Unregister-ScheduledTask -TaskName $n -Confirm:$false -ErrorAction SilentlyContinue }
    "removed: $($names -join ', ')"
    exit 0
}
$pcf = Split-Path $PSScriptRoot -Parent
$repo = Split-Path $pcf -Parent
$live = Join-Path (Split-Path $repo -Parent) "FFInsights-live"
$dataDir = Join-Path $pcf "data"
if (-not (Test-Path $live)) { throw "no live copy at ${live}: run register-ledger-task.ps1 first" }
git -C $repo fetch --quiet origin main
git -C $live checkout --quiet --detach origin/main
if ($LASTEXITCODE -ne 0) { throw "could not update the live copy" }
$script = Join-Path $live "pcf\ops\collect-run.ps1"
if (-not (Test-Path $script)) { throw "main doesn't have collect-run.ps1 yet: merge it, then run this again" }

function Action([string]$what) {
    New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`" -What $what -DataDir `"$dataDir`""
}
$d = $StartDate
$odds = @(
    New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday -At $d.AddHours(10.5)
    New-ScheduledTaskTrigger -Weekly -DaysOfWeek Thursday -At $d.AddHours(15)
    New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday -At $d.AddHours(10.5)
    New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $d.AddHours(7)
    New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At $d.AddHours(15)
)
$daily = New-ScheduledTaskTrigger -Daily -At $d.AddHours(8.5)
$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
Register-ScheduledTask -TaskName $names[0] -Force -Action (Action "odds") -Trigger $odds `
    -Settings $settings -Principal $principal `
    -Description "Collects betting lines into the private pcf-data repo while GitHub Actions is locked (PCF)." | Out-Null
Register-ScheduledTask -TaskName $names[1] -Force -Action (Action "nflverse") -Trigger $daily `
    -Settings $settings -Principal $principal `
    -Description "Records nflverse's daily snapshot into the private pcf-data repo while GitHub Actions is locked (PCF)." | Out-Null
$names | ForEach-Object { Get-ScheduledTask -TaskName $_ | Get-ScheduledTaskInfo | Select-Object TaskName, NextRunTime }
