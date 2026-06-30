param(
    [int]$LimitPerJournal = 100,
    [int]$ScreenLimit = 50,
    [int]$MaxScreenBatches = 10,
    [int]$RefilterLimit = 10,
    [switch]$SkipCoverage,
    [switch]$PushPublicData
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Split-Path -Parent $ScriptDir
$ProjectDir = Split-Path -Parent $BackendDir
$LogDir = Join-Path $BackendDir "data\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogPath = Join-Path $LogDir "weekly_run_$Timestamp.log"

Set-Location $ProjectDir

Start-Transcript -Path $LogPath -Append | Out-Null
try {
    Write-Host "Paper HOT weekly run"
    Write-Host "Project: $ProjectDir"
    Write-Host "Started: $(Get-Date -Format o)"

    $Args = @(
        "-m", "journal_tracker.main",
        "weekly-run",
        "--limit-per-journal", $LimitPerJournal,
        "--screen-limit", $ScreenLimit,
        "--max-screen-batches", $MaxScreenBatches,
        "--refilter-limit", $RefilterLimit
    )
    if ($SkipCoverage) {
        $Args += "--skip-coverage"
    }

    & py @Args
    if ($LASTEXITCODE -ne 0) {
        throw "weekly-run failed with exit code $LASTEXITCODE"
    }

    if ($PushPublicData) {
        git add frontend/public/data/papers.json frontend/public/data/all_papers.json
        $Status = git status --short
        if ($Status) {
            $CommitMessage = "Update weekly public paper data $Timestamp"
            git commit -m $CommitMessage
            git push origin main
        } else {
            Write-Host "No public data changes to commit."
        }
    }

    Write-Host "Finished: $(Get-Date -Format o)"
    Write-Host "Log: $LogPath"
}
finally {
    Stop-Transcript | Out-Null
}
