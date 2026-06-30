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

最近一次本地状态：

```text
Total rows: 50
High: 9
Medium: 3
Low: 18
Pending: 0
Screened: 30
Quarantined: 20
Published featured papers: 8
All journal update rows exported: 23
```

最近一次覆盖验证显示：本地 OpenAlex 库只有 23 个 DOI，而 Crossref 在红榜期刊中查到 581 个 DOI。主要原因是上一次真实 OpenAlex 抓取使用了 `--limit-per-journal 1`，所以当前全量页还不是完整全量。下一步应先提高抓取深度。

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

Because the current local inventory was created with a shallow fetch, run a deeper OpenAlex fetch before further AI prompt work:

```bash
py -m journal_tracker.main fetch-journals --limit-per-journal 100
py -m journal_tracker.main repair-queue
py -m journal_tracker.main export-public
py -m journal_tracker.main verify-coverage
```

After checking how many new `pending` rows appear, run `screen-pending` in batches.

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
