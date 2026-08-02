# Automation

Paper HOT now has two GitHub Actions workflows:

- `.github/workflows/ci.yml` runs Python tests on 3.9 and 3.12, exercises a fresh SQLite database, and runs the frontend logic tests for every push and pull request.
- `.github/workflows/weekly-update.yml` runs every Monday at 13:00 GMT+8 (Asia/Shanghai) and can also be started manually from the Actions page.

## GitHub Repository Setup

Before enabling the weekly workflow, add this Actions secret under **Settings → Secrets and variables → Actions**:

- Secret `ANTHROPIC_API_KEY`: required DeepSeek/Anthropic-compatible API key.

Optional configuration:

- Secret `SEMANTIC_SCHOLAR_API_KEY`: only needed by supplemental Semantic Scholar search.
- Variable `ANTHROPIC_BASE_URL`: overrides `backend/config/settings.yaml` when a different compatible endpoint is required.
- Variable `AI_MODEL`: overrides the checked-in model name.

The workflow requests `contents: write` so its repository-scoped `GITHUB_TOKEN` can commit refreshed `frontend/public/data/*.json` files. If the push is denied, check organization or repository policy under **Settings → Actions → General → Workflow permissions**.

Do not place the real key in `weekly-update.yml`, `settings.yaml`, `.env.example`, a commit, or a workflow input. The workflow injects `ANTHROPIC_API_KEY` only into the preflight and AI workflow steps; checkout, cache, artifact upload, and Git commit steps cannot read it from their environment. GitHub masks registered secret values in normal logs, but the workflow still avoids printing or transforming the key.

The working SQLite database is restored from the latest Actions cache and saved under a run-specific cache key. Public JSON and run reports are also retained as a 30-day workflow artifact. The cache is operational state rather than a permanent backup; if it expires, the workflow safely rebuilds a database from the journal fetch.

The scheduled run performs the existing journal-first workflow, refreshes the README statistics and featured preview, commits public JSON and README only when they changed, and never commits the SQLite database or API keys.

For the first cloud run, start the workflow manually with `commit_public_data` disabled. This lets the job verify the secret, build the cached database, and upload artifacts without replacing the current public feed. Run it again as needed until the cached queue is healthy, inspect the artifact, then enable `commit_public_data` for the first intentional publication. As an additional guard, a scheduled run that starts without a restored database initializes the cache but does not publish; later scheduled runs with restored cloud state commit changed public JSON automatically.

GitHub runs schedules from the latest default-branch commit. For public repositories, GitHub may disable scheduled workflows after 60 days without repository activity; re-enable the workflow from the Actions page if that happens.

Paper HOT currently uses local runtime state:

- `.local/key.env` stores API keys.
- `backend/data/papers.db` stores the working SQLite database.
- `backend/data/reports/` stores coverage and weekly workflow JSON reports.
- `backend/data/logs/` stores scheduled task console transcripts.

Windows Task Scheduler remains available for a machine that must own its database permanently. GitHub Actions is now suitable for the shared weekly public feed, with the cache limitation described above.

## Weekly Command

The canonical weekly workflow is:

```bash
python -m journal_tracker.main weekly-run --limit-per-journal 100 --screen-limit 50 --max-screen-batches 10 --refilter-limit 10
```

It runs:

1. OpenAlex red-list journal fetch.
2. Queue repair.
3. Pending paper screening in bounded batches.
4. Error retry, High-paper publication, and website JSON export.
5. Crossref coverage verification.
6. JSON report export to `backend/data/reports/weekly_run_*.json`.
7. README statistics and latest featured-paper preview refresh.

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

## Longer-Term Production Option

For stronger durability and concurrent editorial use, move SQLite state to a hosted database. The current cache-backed Action is intentionally simple and recoverable, but GitHub does not guarantee Actions cache as permanent storage.
