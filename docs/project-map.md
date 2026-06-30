# Project Map

这份文档用于快速定位 Paper HOT 项目里的文件。原则是：README 讲入口和当前状态，Roadmap 讲下一步，Project Map 讲文件位置和职责。

## Top-Level Files

| Path | Role |
| --- | --- |
| `README.md` | 项目入口文档：目标、当前状态、常用命令、验证方式。 |
| `CLAUDE.md` | 早期 Claude Code 使用说明。部分内容已过时，当前工作请优先看 README 和本文件。 |
| `pyproject.toml` | Python 包配置和依赖声明。 |
| `.gitignore` | 忽略本地数据库、密钥、飞书二维码、工具状态和生成报告。 |
| `.local/key.env` | 本地 API key 文件，已忽略，不应提交。 |

## Local-Only Workspace Files

| Path | Role | Commit? |
| --- | --- | --- |
| `.local/feishu/` | 飞书登录、授权过程中生成的二维码图片。 | No |
| `.local/tool-state/` | 本地工具 lock/state 文件，例如 `skills-lock.json`。 | No |
| `.agents/`, `.claude/`, `.codex/` | 本地 AI agent / Codex / Claude 工具状态。 | No |
| `.local/build-artifacts/journal_tracker.egg-info/` | Python editable install/build 生成物。 | No |

## Core Source Code

| Path | Role |
| --- | --- |
| `backend/journal_tracker/main.py` | CLI 入口。负责 fetch、repair、screen、publish、export、coverage 等命令编排。 |
| `backend/journal_tracker/config.py` | 读取 `backend/config/` 和 `.local/key.env`，提供数据库路径、模型、API key、红榜期刊列表。 |
| `backend/journal_tracker/discovery.py` | 论文发现。包含 Semantic Scholar 关键词检索和 OpenAlex source/ISSN 期刊抓取。 |
| `backend/journal_tracker/filter.py` | AI 筛选。通过 DeepSeek/Anthropic-compatible API 生成 relevance、reason、tags、summary。 |
| `backend/journal_tracker/storage.py` | SQLite 存储。维护 papers 表、去重、队列状态、发布状态和统计。 |
| `backend/journal_tracker/publication.py` | 公开 JSON 导出：精选论文和全量期刊更新。 |
| `backend/journal_tracker/coverage.py` | OpenAlex 本地库存与 Crossref DOI 覆盖验证。 |
| `backend/journal_tracker/notification.py` | 通知发送，占位保留。 |

## Configuration

| Path | Role |
| --- | --- |
| `backend/config/journals.yaml` | 红榜期刊、优先级、OpenAlex source id、ISSN、追踪起始年份。 |
| `backend/config/prompts.yaml` | AI 筛选 prompt 配置。 |
| `backend/config/settings.yaml` | 数据库、模型、通知等运行配置。 |

## Data And Generated Outputs

| Path | Role | Commit? |
| --- | --- | --- |
| `backend/data/papers.db` | 本地 SQLite 数据库。 | No |
| `backend/data/reports/coverage_*.json` | 本地 Crossref 覆盖验证报告。 | No |
| `frontend/public/data/papers.json` | 公开站精选论文数据。 | Yes |
| `frontend/public/data/all_papers.json` | 公开站红榜期刊全量更新数据。 | Yes |

## Website

| Path | Role |
| --- | --- |
| `frontend/web/index.html` | 静态页面结构。 |
| `frontend/web/styles.css` | 页面视觉样式和响应式布局。 |
| `frontend/web/app.js` | 加载 JSON、筛选、搜索、主题切换和 Featured / All Updates 切换。 |
| `frontend/web/app.test.cjs` | 前端纯逻辑测试。 |

## Tests

| Path | Role |
| --- | --- |
| `backend/tests/test_config.py` | 配置读取、key.env、红榜期刊优先级。 |
| `backend/tests/test_discovery.py` | Semantic Scholar 发现、限流、重试和报告。 |
| `backend/tests/test_openalex_discovery.py` | OpenAlex source/ISSN 抓取。 |
| `backend/tests/test_filter.py` | DeepSeek/Anthropic-compatible AI 响应解析。 |
| `backend/tests/test_storage_workflow.py` | 存储字段、队列状态、隔离、CSV 导出。 |
| `backend/tests/test_publication.py` | 发布、公开 JSON、全量 JSON、CLI 发布命令。 |
| `backend/tests/test_journal_workflow.py` | 红榜抓取、coverage CLI 等工作流入口。 |
| `backend/tests/test_coverage.py` | Crossref 覆盖验证逻辑。 |
| `backend/tests/test_notification.py` | 通知开关和空发送行为。 |

## Documentation

| Path | Role |
| --- | --- |
| `docs/roadmap.md` | 当前唯一 TODO / 多阶段路线。 |
| `docs/project-map.md` | 当前文件地图。 |
| `docs/archive/2026-05-10-architecture-review/` | 早期项目结构审计过程文档。 |
| `docs/archive/2026-05-static-site-design/` | 早期静态站设计和实现方案。 |

## Main Commands

```bash
py -m journal_tracker.main workflow-status
py -m journal_tracker.main fetch-journals --limit-per-journal 100
py -m journal_tracker.main repair-queue
py -m journal_tracker.main screen-pending --limit 20
py -m journal_tracker.main export-public
py -m journal_tracker.main verify-coverage
py -m journal_tracker.main update-public
```

## Current Caveats

- `backend/data/papers.db` is local state. GitHub does not contain the local database.
- `frontend/public/data/*.json` are the static website data snapshots and are committed.
- `coverage_latest.json` is a generated local report and is ignored by git.
- The latest coverage report shows the local OpenAlex inventory is shallow because the previous real fetch used `--limit-per-journal 1`.
