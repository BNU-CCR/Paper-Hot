# Agent Notes

This repository is now maintained around three current documents:

- `README.md` for project status and commands.
- `docs/project-map.md` for file and folder responsibilities.
- `docs/roadmap.md` for the active TODO and phased plan.

Historical planning documents are under `docs/archive/`.

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

## Useful Commands

```bash
py -m journal_tracker.main workflow-status
py -m journal_tracker.main fetch-journals --limit-per-journal 100
py -m journal_tracker.main repair-queue
py -m journal_tracker.main screen-pending --limit 20
py -m journal_tracker.main export-public
py -m journal_tracker.main verify-coverage
py -m journal_tracker.main update-public
```

Verification:

```bash
py -m unittest discover backend/tests -v
node frontend\web\app.test.cjs
```
