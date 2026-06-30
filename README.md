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

- 红榜期刊配置：`config/journals.yaml`
- OpenAlex source/ISSN 期刊抓取：`fetch-journals`
- 本地 SQLite 存储和去重：`data/papers.db`
- 队列状态：`pending`、`screened`、`quarantined`
- 历史废数据隔离：`repair-queue`
- DeepSeek / Anthropic-compatible AI 筛选：`screen-pending`
- 精选论文导出：`public/data/papers.json`
- 红榜期刊全量更新导出：`public/data/all_papers.json`
- 静态网站：`web/index.html`
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
├── config/                 # journals, prompts, settings
├── data/                   # local database and generated local reports
├── docs/
│   ├── project-map.md      # what each file/folder does
│   ├── roadmap.md          # current TODO and development phases
│   └── archive/            # historical plans/specs
├── public/data/            # JSON consumed by the static website
├── src/                    # Python CLI and workflow modules
├── tests/                  # unittest test suite
├── web/                    # static website
├── README.md
└── pyproject.toml
```

## Local Setup

Install the package in editable mode:

```bash
py -m pip install -e .
```

Local secrets go in `key.env`, which is ignored by git:

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
py -m src.main workflow-status
```

Fetch red-list journal updates:

```bash
py -m src.main fetch-journals --limit-per-journal 100
```

Repair local queue and quarantine dirty legacy rows:

```bash
py -m src.main repair-queue
```

Screen pending papers with AI:

```bash
py -m src.main screen-pending --limit 20
```

Export website data:

```bash
py -m src.main export-public
```

Verify OpenAlex coverage against Crossref:

```bash
py -m src.main verify-coverage
```

Publish all High papers and refresh website JSON:

```bash
py -m src.main update-public
```

Preview the website locally:

```bash
py -m http.server 8000
```

Then open:

```text
http://127.0.0.1:8000/web/index.html
```

## Recommended Next Run

Because the current local inventory was created with a shallow fetch, run a deeper OpenAlex fetch before further AI prompt work:

```bash
py -m src.main fetch-journals --limit-per-journal 100
py -m src.main repair-queue
py -m src.main export-public
py -m src.main verify-coverage
```

After checking how many new `pending` rows appear, run `screen-pending` in batches.

## Verification

Python tests:

```bash
py -m unittest tests.test_config tests.test_publication tests.test_discovery tests.test_openalex_discovery tests.test_filter tests.test_notification tests.test_journal_workflow tests.test_storage_workflow tests.test_coverage -v
```

Frontend logic tests:

```bash
node web\app.test.cjs
```

## Git Notes

Committed:

- Source code in `src/`
- Tests in `tests/`
- Config templates and journal metadata in `config/`
- Static site in `web/`
- Public website JSON snapshots in `public/data/`
- Current docs in `docs/`

Ignored:

- `key.env`
- `data/papers.db`
- `data/reports/*.json`
- Feishu QR code images
- `.local/` local tool artifacts
- `.agents/`, `.codex/`, `.claude/`
- build/cache artifacts
