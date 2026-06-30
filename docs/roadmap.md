# Paper HOT Roadmap

本文件是当前唯一维护中的 TODO / 路线文档。历史计划、早期审计和视觉方案已归档到 `docs/archive/`。

## Product Goal

Paper HOT 目标是做一个类似 AI HOT 的计算传播论文情报站：

- 以团队红榜期刊为主数据源，按期刊而不是泛关键词抓取。
- 从 2026 年开始追踪红榜期刊论文更新。
- 保留红榜期刊全量更新页。
- 用 AI 筛选出计算传播相关论文，生成摘要、标签和推荐理由。
- 将精选论文发布到静态网站，后续接入定期推送。

## Current State

- Red-list journals are configured in `backend/config/journals.yaml`.
- OpenAlex source/ISSN ingestion is implemented through `fetch-journals`.
- Local SQLite storage supports provenance and queue states: `pending`, `screened`, `quarantined`.
- Historical dirty rows are quarantined with `repair-queue`; they are not physically deleted.
- AI screening runs from the local queue with `screen-pending`.
- Public site data exports:
  - `frontend/public/data/papers.json`: published High papers.
  - `frontend/public/data/all_papers.json`: all red-list OpenAlex journal updates.
- Website supports Featured / All Updates switching.
- Crossref coverage verification is implemented with `verify-coverage`.

Latest verified local state:

- Total rows: 50
- Screened: 30
- Quarantined: 20
- Pending: 0
- Public featured papers: 8
- All journal update rows currently exported: 23
- Coverage report indicates current OpenAlex local inventory is still shallow because the last real journal fetch used `--limit-per-journal 1`.

## Phase 1: Public Site V1

- [x] Implement static site in `frontend/web/`.
- [x] Render public featured papers from `frontend/public/data/papers.json`.
- [x] Support relevance, tag, and search filters.
- [x] Support light / dark / system theme switching.
- [x] Add Featured / All Updates data switching.
- [ ] Add paper detail view or expandable detail state.

## Phase 2: Journal-First Data Loop

- [x] Confirm red-list journal workflow from Feishu list.
- [x] Add OpenAlex source id / ISSN metadata to tracked journals.
- [x] Fetch red-list journal updates through OpenAlex source/ISSN.
- [x] Store fetched papers as `pending`.
- [x] Add queue repair: red-list rows to `pending`, non-red-list dirty rows to `quarantined`.
- [x] Add AI screening for pending queue.
- [x] Export public featured JSON.
- [x] Export all journal updates JSON.
- [x] Add OpenAlex / Crossref DOI coverage verification.
- [ ] Increase OpenAlex fetch depth and refresh local journal inventory.
- [ ] Re-run coverage verification after deeper OpenAlex fetch.
- [ ] Make the default full pipeline journal-first; keep keyword search as supplemental.

## Phase 3: AI Screening Quality

- [ ] Define a clearer computational communication screening rubric.
- [ ] Improve recommendation reasons to avoid generic language.
- [ ] Normalize tag taxonomy by method, object, platform, theory, and data source.
- [ ] Add low-confidence / manual-review queue.
- [ ] Build a small manually labeled benchmark set for prompt regression tests.

## Phase 4: Automation And Logs

- [ ] Persist ingestion run reports as JSON logs.
- [ ] Persist screening run reports as JSON logs.
- [ ] Add a single weekly command that runs fetch, repair, screen, export, and coverage verification.
- [ ] Decide whether scheduling should be local cron / Task Scheduler, GitHub Actions, or external automation.

## Phase 5: Deployment And Push

- [ ] Choose static deployment target: GitHub Pages, Vercel, or Cloudflare Pages.
- [ ] Verify public URL can read `frontend/public/data/papers.json`.
- [ ] Verify public URL can read `frontend/public/data/all_papers.json`.
- [ ] Choose push channel: Feishu, email, RSS, ServerChan, or another feed.
- [ ] Design weekly push template.

## Phase 6: Editorial Tools

- [ ] Add private/editorial management entrypoint.
- [ ] Support editing title, summary, tags, and recommendation reason.
- [ ] Support manual score adjustment.
- [ ] Generate group-meeting sharing cards.

## Immediate Next Step

Run a deeper OpenAlex fetch before spending more effort on AI prompt quality:

```bash
py -m journal_tracker.main fetch-journals --limit-per-journal 100
py -m journal_tracker.main repair-queue
py -m journal_tracker.main export-public
py -m journal_tracker.main verify-coverage
```

Only after the local all-updates inventory is closer to Crossref coverage should new pending papers be screened in bulk.
