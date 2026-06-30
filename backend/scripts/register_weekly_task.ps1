param(
    [string]$TaskName = "Paper HOT Weekly Run",
    [ValidateSet("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")]
    [string]$DayOfWeek = "Monday",
    [string]$At = "09:00",
    [switch]$PushPublicData,
    [switch]$SkipCoverage
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunScript = Join-Path $ScriptDir "run_weekly.ps1"

$RunArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$RunScript`""
)
if ($PushPublicData) {
    $RunArgs += "-PushPublicData"
}
if ($SkipCoverage) {
    $RunArgs += "-SkipCoverage"
}

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument ($RunArgs -join " ")

$Trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek $DayOfWeek `
    -At $At

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 6)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Runs Paper HOT journal-first weekly workflow." `
    -Force

Write-Host "Registered scheduled task: $TaskName"
Write-Host "Schedule: $DayOfWeek at $At"
Write-Host "Script: $RunScript"
