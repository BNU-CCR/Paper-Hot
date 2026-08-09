# Agent Notes

This repository is now maintained around three current documents:

- `README.md` for project status and commands.
- `docs/project-map.md` for file and folder responsibilities.
- `docs/roadmap.md` for the active TODO and phased plan.

Historical planning documents are under `docs/archive/`.

Frontend UI design conventions (shadcn, single heading per section, no placeholder hints) live in `AGENTS.md` — read it before touching frontend code.

## Frontend Commit Convention

- For frontend-only changes under `frontend/` (components, styles, types, or static presentation logic), after typecheck and the production build pass, commit and push directly to `main` by default. Do not create a branch or PR, and do not ask again whether to push.
- If a change also touches the backend, data pipeline, workflows, or another higher-risk area, continue to use the small-PR workflow in `AGENTS.md` unless the user explicitly requests otherwise.
- Before a direct push, confirm the current branch is `main` and keep unrelated working-tree changes out of the commit.

## Current Product Direction

Use the journal-first workflow as the default:

1. Fetch red-list journal updates from OpenAlex by source id / ISSN.
2. Store new papers as `pending`.
3. Quarantine non-red-list dirty legacy rows with `repair-queue`.
4. Screen pending papers with AI.
5. Export public featured papers and all journal updates for the static site.
6. Verify source coverage against Crossref.

## Method Labels (研究方法标签)

AI 筛选在输出主题标签（`tags`）的同时，还会为每篇论文打一个**单一**研究方法标签（`method`），固定分类学：

- 质性分析 / 量化分析 / 理论分析 / 综述 / 计算传播学
- 不确定时留空（`""`）

- 新论文在 `screen-pending` 的同一次 AI 调用里带出 method（prompts.yaml 的 `filter_system_prompt` / `method_labels` / `method_system_prompt` / `method_user_template`）。
- 已筛选的旧论文用 `label-methods` 回填（只更新 method，不扰动 relevance/tags/summary；一次性跑完即可，无需每周执行）。
- method 会随 `export-public` 写入 papers.json / all_papers.json，前端卡片显示徽章并支持按方法筛选。

Keyword search and Semantic Scholar are supplemental, not the primary ingestion path.

## Safety Notes

- Do not commit `.local/key.env`.
- Do not commit `backend/data/papers.db`.
- Do not commit local Feishu QR code images or `.agents/` state.
- `frontend/public/data/papers.json` and `frontend/public/data/all_papers.json` are static website snapshots and can be committed.

## Cloud Secrets & LLM Runs

**API keys live only in the cloud.** `ANTHROPIC_API_KEY` (DeepSeek Anthropic-compatible), `SEMANTIC_SCHOLAR_API_KEY`, and the repo variables (`ANTHROPIC_BASE_URL`, `AI_MODEL`) are GitHub Actions secrets / variables — they are **not** present in local `.env` or the sandbox. `backend/data/papers.db` is likewise only on the Actions cache.

Consequence for development:

- Any code path that actually calls the LLM (AI screening, `label-methods`, hotspot topic labeling) **cannot be executed locally** — there is no key. Smoke-test it locally against **mocks** (see `backend/tests/test_filter.py` for the mock-client pattern), then hand the real run to GitHub Actions (weekly-update / backfill-journals / rebuild-hotspot-network).
- The LLM response layer is fragile against DeepSeek's Anthropic-compatible endpoint: it may return only `thinking` blocks (no usable text) under load. The call sites in `filter.py` (`_call_messages`) and `hotspot_labels.py` retry with backoff and prefer `type == "text"` blocks; keep that behavior when adding new LLM calls.

## Hotspot Network Data (regenerated via GitHub Actions)

`frontend/public/data/hotspots/` (graph.json / trends.json / manifest.json / topics/*.json) is a **build artifact**, not source — the hotspot semantic map is rebuilt in CI, never edited locally.

- `weekly-update.yml` runs `build-hotspot-network` on the weekly schedule and commits the refreshed `frontend/public/data/hotspots/`.
- `rebuild-hotspot-network.yml` is a **dispatch-only** workflow to regenerate the hotspot data from the cached database without fetching/screening papers. Use it after changing hotspot pipeline code: push to git → GitHub → Actions → "Rebuild hotspot network" → Run workflow.
- The workflows need the `ANTHROPIC_API_KEY` secret (topic labels) and restore `backend/data/papers.db` from the Actions cache; if the cache is empty they have no data to build from.
- Workflow commits made with the default `GITHUB_TOKEN` (the rebuild workflow's `git push`) do **not** re-trigger `ci.yml`/`deploy-pages.yml` — that's GitHub's anti-recursion rule. The rebuild workflow already validates + deploys itself, so this is fine; a later manual/push-triggered CI run checks the new data. Until the data is regenerated, a fresh-DB CI smoke test (`build-hotspot-network` then `validate-hotspot-data`) fails because `validate-hotspot-data` validates the **committed** `frontend/public/data/hotspots/` — stale schema-2 data fails the size/trend check.
- Locally `python -m journal_tracker.main build-hotspot-network` needs the `.[analysis]` extras (fastembed / umap / igraph) and the API key — in a sandbox without them, prefer the CI workflow.
- Config for the pipeline lives in `backend/config/settings.yaml` under `hotspot_network` (analysis_days / recent_days / min_recent_papers_for_display / min_recent_papers_for_hot / include_inactive_topics / ...). The display filter means topics with `recent_count <= 1` in the last 30 days stay out of the main graph but remain in `topics_meta` for lineage.

## Backfill Journal Data (year-range catch-up, via GitHub Actions)

The weekly update only fetches works dated `>=` each journal's `track_from_year` (2026), so online-first journals like HCR have almost no 2025 content. To import a full year range:

- `backfill-journals.yml` is a **dispatch-only** workflow (Actions → "Backfill journals (year range)" → Run workflow). It restores the cached DB, runs `backfill-run`, screens, method-labels, rebuilds hotspots, and redeploys + commits.
- Inside `backfill-run` the order is fixed: **backfill → screen → label-methods → publish/export → hotspots** — the method-label update always runs *after* the backfill so newly imported papers get relevance + method in the same pass.
- The workflow shares the `paper-hot-weekly-update` concurrency group with `weekly-update.yml`, so a manual backfill and the scheduled weekly run serialize on the DB cache (no race).
- Cloud order for a one-time catch-up: push code to main → run "Backfill journals (year range)" once → the scheduled weekly keeps feeding new papers from the enlarged DB afterwards.
- `label-methods` is a one-time backfill for papers screened before the method feature existed; new screening already writes `method` in the same AI call, so the weekly update needs no extra step.

## Useful Commands

```bash
python -m journal_tracker.main workflow-status
python -m journal_tracker.main fetch-journals --limit-per-journal 100
python -m journal_tracker.main backfill-journals --from-year 2025 --to-year 2026 --limit-per-journal 1000
python -m journal_tracker.main backfill-run --from-year 2025 --to-year 2026 --screen-limit 50 --max-screen-batches 20 --label-methods-limit 1000
python -m journal_tracker.main repair-queue
python -m journal_tracker.main screen-pending --limit 20
python -m journal_tracker.main label-methods --limit 200
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
