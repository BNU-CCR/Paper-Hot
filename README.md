# Paper HOT / 计算传播期刊追踪

Paper HOT 是一个面向计算传播研究的论文情报站。项目目标是：以团队红榜期刊为稳定数据源，定期抓取 2026 年以来的论文更新，保留期刊全量更新，再用 AI 筛选出计算传播相关论文，生成摘要、标签和推荐理由，并发布到静态网站和后续推送渠道。

<!-- paper-hot:auto-preview:start -->
## 本期精选（自动更新）

> 更新于 2026-08-02 10:45 GMT+8，展示最新 5 篇精选论文。

| 日期 | 论文 | 期刊 | 推荐摘要 |
| --- | --- | --- | --- |
| 2026-06-28 | [Is Flattery in AI Fact-Checking Helpful or Harmful? Effects on Tool Favorability and Epistemic Verification](<https://doi.org/10.1080/08838151.2026.2694043>) | Journal of Broadcasting & Electronic Media | 实验研究AI事实核查中奉承语气的影响，发现其提升工具偏好但降低信息回忆与参考核查，无关初始答案正确性。 |
| 2026-06-26 | [Beyond the Black Box: Human-AI Collaboration and Algorithmic Accountability in Arabic-Language Fact-Checking](<https://doi.org/10.1080/08838151.2026.2694044>) | Journal of Broadcasting & Electronic Media | 通过访谈和案例分析，研究AI在阿拉伯语事实核查中的整合，强调人机混合模式、透明性和文化适配性。 |
| 2026-06-26 | [From Mass Media and Social Media to AI: A Multilevel Framework for Understanding Trust in Generative AI](<https://doi.org/10.1080/08838151.2026.2694048>) | Journal of Broadcasting & Electronic Media | 提出多层次框架，从大众媒体、社交媒体到AI，分析对生成式AI的信任构建机制。 |
| 2026-06-26 | [AI as “Artificial Immigrants”? A Content Analysis of the U.S. News Media Framing of AI Threats](<https://doi.org/10.1080/08838151.2026.2692543>) | Journal of Broadcasting & Electronic Media | 基于整合威胁理论，分析美国新闻媒体对AI威胁的框架，发现现实威胁强调多于象征威胁，技术报道偏向现实框架。 |
| 2026-06-26 | [Trust in ChatGPT for political information consumption: the roles of use, perceived threat, and political ideology](<https://doi.org/10.1080/19331681.2026.2682924>) | Journal of Information Technology & Politics | 探讨用户对ChatGPT的信任度及其在政治信息消费中的影响，分析使用行为、感知威胁和政治意识形态的作用 |

<!-- paper-hot:auto-preview:end -->

## Where To Start

- 文件地图：[`docs/project-map.md`](docs/project-map.md)
- 当前路线：[`docs/roadmap.md`](docs/roadmap.md)
- 文件夹结构复盘：[`docs/workspace-structure-review.md`](docs/workspace-structure-review.md)
- 自动化运行：[`docs/automation.md`](docs/automation.md)
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
- Windows Task Scheduler 本地调度脚本：`backend/scripts/run_weekly.ps1`

<!-- paper-hot:auto-stats:start -->
### 自动更新状态

> 最近更新：2026-08-02 10:45 GMT+8

| 指标 | 数量 |
| --- | ---: |
| 数据库论文 | 548 |
| 当期新增 | 0 |
| High / Medium / Low | 137 / 69 / 342 |
| Pending / Screened / Quarantined / Error | 0 / 547 / 0 / 1 |
| 已发布精选 | 139 |
| 期刊全量导出 | 548 |

<!-- paper-hot:auto-stats:end -->

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
python3 -m venv venv
source venv/bin/activate
python -m pip install -e .
```

On Windows, activate with `venv\\Scripts\\activate` and use `py -m pip install -e .`.

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
python -m journal_tracker.main workflow-status
```

Fetch red-list journal updates:

```bash
python -m journal_tracker.main fetch-journals --limit-per-journal 100
```

Repair local queue and quarantine dirty legacy rows:

```bash
python -m journal_tracker.main repair-queue
```

Screen pending papers with AI:

```bash
python -m journal_tracker.main screen-pending --limit 20
```

Export website data:

```bash
python -m journal_tracker.main export-public
```

Refresh the README statistics and featured preview:

```bash
python -m journal_tracker.readme_update
```

Verify OpenAlex coverage against Crossref:

```bash
python -m journal_tracker.main verify-coverage
```

Run the journal-first weekly workflow:

```bash
python -m journal_tracker.main weekly-run --limit-per-journal 100 --screen-limit 50 --max-screen-batches 10 --refilter-limit 10
```

Run the same workflow through the Windows automation wrapper:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_weekly.ps1
```

Publish all High papers and refresh website JSON:

```bash
python -m journal_tracker.main update-public
```

Preview the website locally:

```bash
python -m http.server 8000
```

Then open:

```text
http://127.0.0.1:8000/frontend/web/index.html
```

## Recommended Next Run

The latest deep fetch and bulk screening have completed. For the next routine refresh, run:

```bash
python -m journal_tracker.main weekly-run --limit-per-journal 100 --screen-limit 50 --max-screen-batches 10 --refilter-limit 10
```

Before the next large screening run, improve the AI response parser and prompt because one paper still remains in `screening_status = error` after retries.

## Verification

Python tests:

```bash
python -m unittest discover backend/tests -v
```

Frontend logic tests:

```bash
node frontend\web\app.test.cjs
```

## GitHub Actions

- `CI` runs the Python test suite on Python 3.9 and 3.12, smoke-tests a fresh database, and runs the frontend tests on every push and pull request.
- `Weekly paper update` runs every Monday at 13:00 GMT+8 (Asia/Shanghai), refreshes this README preview and statistics, and supports manual runs with smaller limits.
- Configure the required `ANTHROPIC_API_KEY` Actions secret before starting the weekly workflow. See [`docs/automation.md`](docs/automation.md) for permissions, optional variables, database caching, and recovery details.

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
