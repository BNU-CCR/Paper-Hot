# Automation

Paper HOT currently uses local runtime state:

- `.local/key.env` stores API keys.
- `backend/data/papers.db` stores the working SQLite database.
- `backend/data/reports/` stores coverage and weekly workflow JSON reports.
- `backend/data/logs/` stores scheduled task console transcripts.

Because of that, the safest scheduling option right now is Windows Task Scheduler on the same machine that owns the local database and API keys.

## Weekly Command

The canonical weekly workflow is:

```bash
py -m journal_tracker.main weekly-run --limit-per-journal 100 --screen-limit 50 --max-screen-batches 10 --refilter-limit 10
```

It runs:

1. OpenAlex red-list journal fetch.
2. Queue repair.
3. Pending paper screening in bounded batches.
4. Error retry, High-paper publication, and website JSON export.
5. Crossref coverage verification.
6. JSON report export to `backend/data/reports/weekly_run_*.json`.

## Manual Windows Run

From the project root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_weekly.ps1
```

Optional parameters:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_weekly.ps1 `
  -LimitPerJournal 100 `
  -ScreenLimit 50 `
  -MaxScreenBatches 10 `
  -RefilterLimit 10
```

To skip Crossref coverage verification during a quick local run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_weekly.ps1 -SkipCoverage
```

To commit and push updated public JSON after the run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_weekly.ps1 -PushPublicData
```

Only use `-PushPublicData` on a machine where GitHub authentication is already configured.

## Register Windows Task

Register a weekly local scheduled task:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\register_weekly_task.ps1 `
  -TaskName "Paper HOT Weekly Run" `
  -DayOfWeek Monday `
  -At "09:00"
```

With automatic public JSON push:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\register_weekly_task.ps1 `
  -TaskName "Paper HOT Weekly Run" `
  -DayOfWeek Monday `
  -At "09:00" `
  -PushPublicData
```

The registration script is committed for reuse, but it should be run manually when the schedule is confirmed.

## Production Options

Windows Task Scheduler is the current default because it can reuse the local database and `.local/key.env`.

GitHub Actions is attractive after deployment, but it needs a production data strategy first:

- Where does `papers.db` live?
- Should generated public JSON be committed by CI or uploaded as an artifact?
- Where are DeepSeek and Semantic Scholar keys stored?
- How are failed runs reported?

External automation is viable if the project later moves the database to a hosted store.
