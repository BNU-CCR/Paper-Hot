# Paper HOT / 计算传播期刊追踪

Paper HOT 是一个面向计算传播研究的论文情报站。项目目标是：以团队红榜期刊为稳定数据源，定期抓取 2026 年以来的论文更新，保留期刊全量更新，再用 AI 筛选出计算传播相关论文，生成摘要、标签和推荐理由，并发布到静态网站和后续推送渠道。

<!-- paper-hot:auto-preview:start -->
## 本期精选（自动更新）

> 更新于 2026-10-08 19:55 GMT+8，展示最新 5 篇精选论文。

| 日期 | 论文 | 期刊 | 推荐摘要 |
| --- | --- | --- | --- |
| 2026-10-05 | [Does the TikTok Feed Lean Right? Exposure to Political Content Among Non-Partisan Users in Germany](<https://doi.org/10.1080/10584609.2026.2733320>) | Political Communication | 研究在德国三场州选与2025联邦选举前，用118个自动化非党派账号审计TikTok推荐流（26.6万条视频），发现政治内容占5%–7%，且非党派用户更易接触极右翼AfD相关内容，该党账号量与爆款视频也更多。 |
| 2026-10-04 | [From Facebook to front page: the influence of the Gilets Jaunes’ social media on local press language and framing](<https://doi.org/10.1080/1369118x.2026.2740032>) | Information Communication & Society | 考察法国黄马甲运动在 Facebook 上的话语如何影响地方报纸的语言使用与新闻框架，涉及社交媒体与主流媒体间的话语流动与议程互动。 |
| 2026-10-01 | [When Populism? Consistent and Opportunistic Populist Communication in the 2022 Brazilian Presidential Elections](<https://doi.org/10.1080/10584609.2026.2735922>) | Political Communication | 基于2022年巴西大选九名候选人11,885条推文，用微调BERT分类器测量民粹主义话语与政策领域，发现民粹传播因候选人策略和议题而异，提出机会型与一致型民粹主义者类型学。 |
| 2026-10-01 | [Skewed toward uniformity? Investigating algorithmic stereotyping and amplification in AI-generated images](<https://doi.org/10.1080/1369118x.2026.2740745>) | Information Communication & Society | 该研究以Draw-a-Scientist框架审计DALL·E 3生成的科学家图像，对比Google Images，通过16项刻板印象指标与潜类别分析识别六类刻板呈现模式，发现DALL·E强化了刻板印象并造成'认知窄化'，讨论算法可见性及缓解策略。 |
| 2026-09-30 | [Skin Tone as a Visual Cue in Political Campaigns: Evidence from Elections in Mexico](<https://doi.org/10.1177/19401612261484045>) | The International Journal of Press/Politics | 论文利用计算视觉分析考察2024年墨西哥联邦选举中候选人肤色与选举成功的关系，并纳入新闻报道、政治广告和社交媒体使用等变量，发现肤色虽与得票率负相关，但媒体因素更重要。 |

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
- Next.js / React 网站（TypeScript + Tailwind CSS v4 + shadcn/ui，RSC 构建时预渲染数据）：首页论文筛选与独立关于页
- 期刊书库：`/journals/` 提供期刊书封、出版社与追踪等级浏览
- Featured / All Updates 切换
- OpenAlex / Crossref DOI 覆盖验证：`verify-coverage`
- 每周期刊优先工作流：`weekly-run`
- Windows Task Scheduler 本地调度脚本：`backend/scripts/run_weekly.ps1`
- 热点语义地图 `/hotspots/`：论文 embedding 经 UMAP 降维后由 [Cosmograph](https://cosmograph.app/)（WebGL）渲染为主题云团，Leiden 主题按色区分、云团中央显示主题名，点击突出核心论文与主题关系。

## 许可说明

- 前端热点图谱使用 [`@cosmograph/react`](https://www.npmjs.com/package/@cosmograph/react)，其许可为 **CC-BY-NC-4.0（仅限非商业使用）**。本项目为学术研究用途，符合该条款；若将来用于商业发布，需替换或购买相应许可。

<!-- paper-hot:auto-stats:start -->
### 自动更新状态

> 最近更新：2026-10-08 19:55 GMT+8

| 指标 | 数量 |
| --- | ---: |
| 数据库论文 | 2117 |
| 当期新增 | 23 |
| High / Medium / Low | 599 / 665 / 853 |
| Pending / Screened / Quarantined / Error | 0 / 2117 / 0 / 0 |
| 已发布精选 | 599 |
| 期刊全量导出 | 2117 |

覆盖验证：OpenAlex DOI 2103，Crossref DOI 872，匹配 820，Crossref 中尚缺 52。

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
│   ├── app/                # Next.js App Router pages and components
│   ├── public/data/        # JSON consumed by the website
│   └── package.json        # React / Next.js scripts and dependencies
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

Run the website locally:

```bash
pnpm --dir frontend install
pnpm --dir frontend dev
```

Then open the local URL shown by Next.js (normally `http://localhost:3000`).

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

Frontend production build:

```bash
pnpm --dir frontend build
```

Frontend type check:

```bash
pnpm --dir frontend typecheck
```

## GitHub Actions

- `CI` runs the Python test suite on Python 3.9 and 3.12, smoke-tests a fresh database, and builds the Next.js frontend on every push and pull request.
- `Weekly paper update` runs every Monday at 13:00 GMT+8 (Asia/Shanghai), refreshes this README preview and statistics, and supports manual runs with smaller limits.
- `Deploy frontend to GitHub Pages` publishes the static website after changes to the frontend or public paper JSON. Once GitHub Pages is enabled for the repository, the site is available at `https://bnu-ccr.github.io/Paper-Hot/`.
- Configure the required `ANTHROPIC_API_KEY` Actions secret before starting the weekly workflow. See [`docs/automation.md`](docs/automation.md) for permissions, optional variables, database caching, and recovery details.

## Git Notes

Committed:

- Backend source code in `backend/journal_tracker/`
- Backend tests in `backend/tests/`
- Config templates and journal metadata in `backend/config/`
- Next.js / React frontend in `frontend/app/`
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
