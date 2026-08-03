# Agent Notes

This repository is now maintained around three current documents:

- `README.md` for project status and commands.
- `docs/project-map.md` for file and folder responsibilities.
- `docs/roadmap.md` for the active TODO and phased plan.

Historical planning documents are under `docs/archive/`.

Frontend UI design conventions (shadcn, single heading per section, no placeholder hints) live in `AGENTS.md` — read it before touching frontend code.

## Current Product Direction

Use the journal-first workflow as the default:

1. Fetch red-list journal updates from OpenAlex by source id / ISSN.
2. Store new papers as `pending`.
3. Quarantine non-red-list dirty legacy rows with `repair-queue`.
4. Screen pending papers with AI.
5. Export public featured papers and all journal updates for the static site.
6. Verify source coverage against Crossref.

Keyword search and Semantic Scholar are supplemental, not the primary ingestion path.

## Safety Notes

- Do not commit `.local/key.env`.
- Do not commit `backend/data/papers.db`.
- Do not commit local Feishu QR code images or `.agents/` state.
- `frontend/public/data/papers.json` and `frontend/public/data/all_papers.json` are static website snapshots and can be committed.

## Hotspot Network Data (regenerated via GitHub Actions)

`frontend/public/data/hotspots/` (graph.json / trends.json / manifest.json / topics/*.json) is a **build artifact**, not source — the hotspot semantic map is rebuilt in CI, never edited locally.

- `weekly-update.yml` runs `build-hotspot-network` on the weekly schedule and commits the refreshed `frontend/public/data/hotspots/`.
- `rebuild-hotspot-network.yml` is a **dispatch-only** workflow to regenerate the hotspot data from the cached database without fetching/screening papers. Use it after changing hotspot pipeline code: push to git → GitHub → Actions → "Rebuild hotspot network" → Run workflow.
- The workflows need the `ANTHROPIC_API_KEY` secret (topic labels) and restore `backend/data/papers.db` from the Actions cache; if the cache is empty they have no data to build from.
- Workflow commits made with the default `GITHUB_TOKEN` (the rebuild workflow's `git push`) do **not** re-trigger `ci.yml`/`deploy-pages.yml` — that's GitHub's anti-recursion rule. The rebuild workflow already validates + deploys itself, so this is fine; a later manual/push-triggered CI run checks the new data. Until the data is regenerated, a fresh-DB CI smoke test (`build-hotspot-network` then `validate-hotspot-data`) fails because `validate-hotspot-data` validates the **committed** `frontend/public/data/hotspots/` — stale schema-2 data fails the size/trend check.
- Locally `python -m journal_tracker.main build-hotspot-network` needs the `.[analysis]` extras (fastembed / umap / igraph) and the API key — in a sandbox without them, prefer the CI workflow.
- Config for the pipeline lives in `backend/config/settings.yaml` under `hotspot_network` (analysis_days / recent_days / min_recent_papers_for_display / min_recent_papers_for_hot / include_inactive_topics / ...). The display filter means topics with `recent_count <= 1` in the last 30 days stay out of the main graph but remain in `topics_meta` for lineage.

## Useful Commands

```bash
python -m journal_tracker.main workflow-status
python -m journal_tracker.main fetch-journals --limit-per-journal 100
python -m journal_tracker.main repair-queue
python -m journal_tracker.main screen-pending --limit 20
python -m journal_tracker.main export-public
python -m journal_tracker.main verify-coverage
python -m journal_tracker.main update-public
python -m journal_tracker.main weekly-run --limit-per-journal 100 --screen-limit 50 --max-screen-batches 10 --refilter-limit 10
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_weekly.ps1
```

Verification:

```bash
python -m unittest discover backend/tests -v
node frontend\web\app.test.cjs
```
