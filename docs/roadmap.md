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
- The journal-first weekly workflow is implemented with `weekly-run`.
- Windows Task Scheduler wrapper scripts are available under `backend/scripts/`.

Latest verified local state:

- Total rows: 575
- Screened: 554
- Quarantined: 20
- Pending: 0
- Public featured papers: 139
- All journal update rows currently exported: 548
- Screening errors: 1
- Coverage report: OpenAlex DOI total 548, Crossref DOI total 582, matched DOI total 543, missing in OpenAlex 39.

## Frontend Stack Migration

已完成的前端技术栈迁移（小 PR 1–4，2026-08）：

- [x] 全部组件从 JS 迁移到 **TypeScript / TSX**（`strict: true`），新增 `frontend/types/` 共享类型定义。
- [x] 引入 **Tailwind CSS v4**，CSS 变量通过 `@theme inline` 映射为设计 token；`dark:` 变体绑定 `[data-theme="dark"]`。
- [x] UI 组件替换为标准 **shadcn/ui v4** 封装（Button / Input / Select / Tabs / Sheet / Collapsible），删除手写 `ui-*` CSS。
- [x] 数据获取改为 **RSC-first**：`frontend/lib/data.ts` 在构建时读 JSON 预渲染，移除 client `useEffect` fetch。
- [x] 验证命令 `pnpm --dir frontend typecheck` + `pnpm --dir frontend build` 全部通过。

## Phase 1: Public Site V1

- [x] Migrate the public site to Next.js / React in `frontend/app/`.
- [x] Render public featured papers from `frontend/public/data/papers.json`.
- [x] Support relevance, tag, and search filters.
- [x] Support light / dark / system theme switching.
- [x] Add Featured / All Updates data switching.
- [x] Add journal filtering, collapsible topic tags, and an independent About page.
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
- [x] Increase OpenAlex fetch depth and refresh local journal inventory.
- [x] Re-run coverage verification after deeper OpenAlex fetch.
- [x] Make the default full pipeline journal-first; keep keyword search as supplemental.

## Phase 3: AI Screening Quality

- [ ] Define a clearer computational communication screening rubric.
- [ ] Improve recommendation reasons to avoid generic language.
- [ ] Normalize tag taxonomy by method, object, platform, theory, and data source.
- [ ] Add low-confidence / manual-review queue.
- [ ] Build a small manually labeled benchmark set for prompt regression tests.

## Phase 4: Automation And Logs

- [x] Persist ingestion run reports as JSON logs.
- [x] Persist screening run reports as JSON logs.
- [x] Add a single weekly command that runs fetch, repair, screen, export, and coverage verification.
- [x] Decide whether scheduling should be local cron / Task Scheduler, GitHub Actions, or external automation.

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

The deep fetch, bulk screening round, journal-first weekly command, and local scheduling wrapper are complete. The current automation default is Windows Task Scheduler because API keys and `papers.db` are local.

```bash
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_weekly.ps1
```

Next, move to deployment: choose GitHub Pages, Vercel, or Cloudflare Pages, then decide whether scheduled runs should also push refreshed public JSON.
