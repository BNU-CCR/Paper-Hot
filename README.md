# Paper HOT / 计算传播期刊追踪

Paper HOT 是一个面向计算传播研究的论文情报站。项目目标是：以团队红榜期刊为稳定数据源，定期抓取 2026 年以来的论文更新，保留期刊全量更新，再用 AI 筛选出计算传播相关论文，生成摘要、标签和推荐理由，并发布到静态网站和后续推送渠道。

## Where To Start

- 文件地图：[`docs/project-map.md`](docs/project-map.md)
- 当前路线：[`docs/roadmap.md`](docs/roadmap.md)
- 文件夹结构复盘：[`docs/workspace-structure-review.md`](docs/workspace-structure-review.md)
- 早期设计和过程文档：[`docs/archive/`](docs/archive/)

根目录只保留项目入口和必要配置。旧的 `task_plan.md`、`findings.md`、`progress.md` 已归档到 `docs/archive/2026-05-10-architecture-review/`。

## Current State

已完成：

- 红榜期刊配置：`backend/config/journals.yaml`
- OpenAlex source/ISSN 期刊抓取：`fetch-journals`
- 本地 SQLite 存储和去重：`backend/data/papers.db`
- 队列状态：`pending`、`screened`、`quarantined`
- 历史废数据隔离：`repair-queue`
- DeepSeek / Anthropic-compatible AI 筛选：`screen-pending`
- 精选论文导出：`frontend/public/data/papers.json`
- 红榜期刊全量更新导出：`frontend/public/data/all_papers.json`
- 静态网站：`frontend/web/index.html`
- Featured / All Updates 切换
- OpenAlex / Crossref DOI 覆盖验证：`verify-coverage`
- 每周期刊优先工作流：`weekly-run`

最近一次本地状态：

```text
Total rows: 575
High: 140
Medium: 69
Low: 346
Pending: 0
Screened: 554
Quarantined: 20
Published featured papers: 139
All journal update rows exported: 548
Screening errors: 1
```

最近一次覆盖验证显示：本地 OpenAlex 库有 548 个 DOI，Crossref 在红榜期刊中查到 582 个 DOI，匹配 543 个 DOI，仍有 39 个 Crossref DOI 未进入 OpenAlex 本地库。深度抓取已经完成，下一步重点转向筛选质量、错误重试和自动化工作流。

## Project Layout

```text
.
├── backend/
│   ├── config/             # journals, prompts, settings
│   ├── data/               # local database and generated local reports
│   ├── journal_tracker/    # Python CLI and workflow modules
│   ├── scripts/            # backend helper scripts
│   └── tests/              # unittest test suite
├── docs/
│   ├── project-map.md      # what each file/folder does
│   ├── roadmap.md          # current TODO and development phases
│   └── archive/            # historical plans/specs
├── frontend/
│   ├── public/data/        # JSON consumed by the static website
│   └── web/                # static website
├── README.md
└── pyproject.toml
```

## Local Setup

Install the package in editable mode:

```bash
py -m pip install -e .
```

Local secrets go in `.local/key.env`, which is ignored by git:

```env
ANTHROPIC_API_KEY=your DeepSeek API key
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
AI_MODEL=deepseek-v4-flash
SEMANTIC_SCHOLAR_API_KEY=your Semantic Scholar API key
SERVERCHAN_SCKEY=optional
```

OpenAlex and Crossref do not require local API keys.

## Main Commands

Check current state:

```bash
py -m journal_tracker.main workflow-status
```

Fetch red-list journal updates:

```bash
py -m journal_tracker.main fetch-journals --limit-per-journal 100
```

Repair local queue and quarantine dirty legacy rows:

```bash
py -m journal_tracker.main repair-queue
```

Screen pending papers with AI:

```bash
py -m journal_tracker.main screen-pending --limit 20
```

Export website data:

```bash
py -m journal_tracker.main export-public
```

Verify OpenAlex coverage against Crossref:

```bash
py -m journal_tracker.main verify-coverage
```

Run the journal-first weekly workflow:

```bash
py -m journal_tracker.main weekly-run --limit-per-journal 100 --screen-limit 50 --max-screen-batches 10 --refilter-limit 10
```

Publish all High papers and refresh website JSON:

```bash
py -m journal_tracker.main update-public
```

Preview the website locally:

```bash
py -m http.server 8000
```

Then open:

```text
http://127.0.0.1:8000/frontend/web/index.html
```

## Recommended Next Run

The latest deep fetch and bulk screening have completed. For the next routine refresh, run:

```bash
py -m journal_tracker.main weekly-run --limit-per-journal 100 --screen-limit 50 --max-screen-batches 10 --refilter-limit 10
```

Before the next large screening run, improve the AI response parser and prompt because one paper still remains in `screening_status = error` after retries.

## Verification

Python tests:

```bash
py -m unittest discover backend/tests -v
```

Frontend logic tests:

```bash
node frontend\web\app.test.cjs
```

## Git Notes

Committed:

- Backend source code in `backend/journal_tracker/`
- Backend tests in `backend/tests/`
- Config templates and journal metadata in `backend/config/`
- Static site in `frontend/web/`
- Public website JSON snapshots in `frontend/public/data/`
- Current docs in `docs/`

Ignored:

- `.local/key.env`
- `backend/data/papers.db`
- `backend/data/reports/*.json`
- Feishu QR code images
- `.local/` local tool artifacts
- `.agents/`, `.codex/`, `.claude/`
- build/cache artifacts
