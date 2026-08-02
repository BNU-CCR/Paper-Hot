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
| `backend/journal_tracker/main.py` | CLI 入口。负责 fetch、repair、screen、publish、export、coverage、build-hotspot-network 等命令编排。 |
| `backend/journal_tracker/config.py` | 读取 `backend/config/` 和 `.local/key.env`，提供数据库路径、模型、API key、红榜期刊列表、热点网络参数。 |
| `backend/journal_tracker/discovery.py` | 论文发现。包含 Semantic Scholar 关键词检索和 OpenAlex source/ISSN 期刊抓取；OpenAlex 抓取附带 topics/keywords/referenced_works。 |
| `backend/journal_tracker/filter.py` | AI 筛选。通过 DeepSeek/Anthropic-compatible API 生成 relevance、reason、tags、summary。 |
| `backend/journal_tracker/storage.py` | SQLite 存储。维护 papers 表、paper_features 表（向量/OpenAlex 增强）、去重、队列状态、发布状态和统计。 |
| `backend/journal_tracker/publication.py` | 公开 JSON 导出：精选论文和全量期刊更新。 |
| `backend/journal_tracker/coverage.py` | OpenAlex 本地库存与 Crossref DOI 覆盖验证。 |
| `backend/journal_tracker/hotspot_network.py` | 热点网络流水线：FastEmbed 向量 → mutual kNN → 混合边权 → Leiden 聚类 → 匈牙利主题匹配 → 热度评分 → 固定布局 → 原子化静态 JSON 输出。 |
| `backend/journal_tracker/hotspot_labels.py` | LLM 批量中文主题命名，带 SHA256 指纹缓存；失败回退英文名。 |
| `backend/journal_tracker/hotspot_validation.py` | 热点静态 JSON 的 schema 校验与原子替换前检查。 |
| `backend/journal_tracker/readme_update.py` | 根据公开 JSON 和每周报告更新 README 统计与当期精选预览。 |
| `backend/journal_tracker/notification.py` | 通知发送，占位保留。 |

## Configuration

| Path | Role |
| --- | --- |
| `backend/config/journals.yaml` | 红榜期刊、优先级、OpenAlex source id、ISSN、追踪起始年份。 |
| `backend/config/prompts.yaml` | AI 筛选 prompt 配置。 |
| `backend/config/settings.yaml` | 数据库、模型、通知、热点网络参数等运行配置。 |
| `backend/config/topic_overrides.yaml` | 热点主题人工重命名与合并规则。 |

## Data And Generated Outputs

| Path | Role | Commit? |
| --- | --- | --- |
| `backend/data/papers.db` | 本地 SQLite 数据库。 | No |
| `backend/data/reports/coverage_*.json` | 本地 Crossref 覆盖验证报告。 | No |
| `.cache/fastembed/` | 本地嵌入模型缓存（CI 恢复/保存）。 | No |
| `frontend/public/data/papers.json` | 公开站精选论文数据。 | Yes |
| `frontend/public/data/all_papers.json` | 公开站红榜期刊全量更新数据。 | Yes |
| `frontend/public/data/hotspots/` | 热点网络静态数据：manifest.json、graph.json、trends.json、topics/*.json。 | Yes |

## Website

| Path | Role |
| --- | --- |
| `frontend/package.json` | Next.js / React 前端脚本和锁定依赖。 |
| `frontend/app/page.tsx` | 首页 RSC：构建时读数据并渲染 `HomeFeed`。 |
| `frontend/components/home-feed.tsx` | 首页 client 组件：精选/全量切换、搜索、相关性、期刊和可收起主题标签筛选。 |
| `frontend/app/hotspots/page.tsx` | 当期热点页 RSC：构建时读图谱/趋势/manifest 数据，交给 `page-client.tsx`。 |
| `frontend/app/hotspots/page-client.tsx` | 热点页 client 组件：图谱/趋势排行/议题概览三 Tab 切换。 |
| `frontend/components/hotspots/hotspot-network.tsx` | Sigma.js + Graphology 交互网络图谱组件。 |
| `frontend/components/hotspots/hotspot-detail-panel.tsx` | 主题详情面板（运行时按需加载 `topics/<id>.json`）。 |
| `frontend/components/hotspots/hotspot-trend-table.tsx` | 主题趋势排行表格。 |
| `frontend/lib/data-url.ts` | 浏览器安全的公开数据 URL 构建（含 basePath）。 |
| `frontend/app/journals/page.tsx` | 独立期刊书库页：书架浏览、出版社和追踪等级筛选。 |
| `frontend/app/journals/[slug]/page.tsx` | 期刊精读页 RSC：读数据并渲染 `JournalReadingList`。 |
| `frontend/app/about/page.tsx` | 独立关于页和 GitHub 项目链接。 |
| `frontend/components/journal-reading-list.tsx` | 期刊精读 client 组件：精选/全部切换、按日期或按 Issue 分组。 |
| `frontend/components/app-sidebar.tsx` | 侧边栏与移动端抽屉导航、主题切换。 |
| `frontend/components/ui/` | shadcn/ui v4 封装组件（Button / Input / Select / Tabs / Sheet / Collapsible）。 |
| `frontend/lib/data.ts` | 构建时读取 `public/data/*.json` 的 server-only 数据模块。 |
| `frontend/types/` | 共享 TypeScript 类型（`paper.ts`、`journal.ts`、`hotspot.ts`）。 |
| `frontend/app/globals.css` | Tailwind v4 入口、`@theme inline` token 映射、页面视觉样式和响应式布局。 |
| `frontend/src/journal-covers.ts` | 期刊封面视觉资产、ISSN、出版社来源和书库元数据。 |
| `frontend/next.config.mts` | 静态导出与 GitHub Pages 子路径配置。 |

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
| `backend/tests/test_readme_update.py` | README 自动统计、精选预览和标记替换。 |
| `backend/tests/test_hotspot_network.py` | 热点网络单元测试 + 合成数据库完整流水线集成测试。 |
| `backend/tests/test_hotspot_validation.py` | 热点静态 JSON 校验逻辑。 |
| `backend/tests/test_paper_features.py` | paper_features 表存取与分析候选查询。 |

## Documentation

| Path | Role |
| --- | --- |
| `docs/roadmap.md` | 当前唯一 TODO / 多阶段路线。 |
| `docs/project-map.md` | 当前文件地图。 |
| `docs/automation.md` | 本地 Windows Task Scheduler 自动化方案。 |
| `docs/archive/2026-05-10-architecture-review/` | 早期项目结构审计过程文档。 |
| `docs/archive/2026-05-static-site-design/` | 早期静态站设计和实现方案。 |

## Main Commands

```bash
python -m journal_tracker.main workflow-status
python -m journal_tracker.main fetch-journals --limit-per-journal 100
python -m journal_tracker.main repair-queue
python -m journal_tracker.main screen-pending --limit 20
python -m journal_tracker.main export-public
python -m journal_tracker.main verify-coverage
python -m journal_tracker.main update-public
python -m journal_tracker.main build-hotspot-network --analysis-days 180 --recent-days 30 --baseline-days 150 --max-topics 40
python -m journal_tracker.main validate-hotspot-data
python -m journal_tracker.main weekly-run --limit-per-journal 100 --screen-limit 50 --max-screen-batches 10 --refilter-limit 10
python -m journal_tracker.readme_update
pnpm --dir frontend install
pnpm --dir frontend build
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_weekly.ps1
```

## Current Caveats

- `backend/data/papers.db` is local state. GitHub does not contain the local database.
- `frontend/public/data/*.json` are the Next.js static website data snapshots and are committed.
- `coverage_latest.json` is a generated local report and is ignored by git.
- The latest coverage report shows the local OpenAlex inventory is shallow because the previous real fetch used `--limit-per-journal 1`.
