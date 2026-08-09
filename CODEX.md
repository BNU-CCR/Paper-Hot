# Codex Project Notes

Codex 在本仓库工作前应先阅读：

- `AGENTS.md`：前端技术栈、设计规范与验证要求。
- `CLAUDE.md`：当前产品方向、数据管线、方法标签与云端工作流约定。
- `README.md`、`docs/project-map.md`、`docs/roadmap.md`：项目状态、目录职责与待办。

## 云端数据与密钥

本项目依赖远端 GitHub Actions 维护真实数据：

- `ANTHROPIC_API_KEY`、`SEMANTIC_SCHOLAR_API_KEY` 只存在于 GitHub Actions secrets。
- `ANTHROPIC_BASE_URL`、`AI_MODEL` 只配置在 GitHub Actions variables。
- `backend/data/papers.db` 的有效版本保存在 Actions cache，本地仓库没有完整工作数据库。
- 不要向本地索取、补写或提交任何真实 API key，也不要提交 `.local/key.env` 或 `backend/data/papers.db`。

因此，本地只运行不需要真实密钥的检查（类型检查、静态构建、JSON 校验、mock 单测）。凡是涉及真实抓取、LLM 筛选、方法回填、热点主题标注或完整数据更新，都必须：

1. 先提交并推送代码；
2. 手动触发对应的 `.github/workflows/*.yml`；
3. 监控 Actions 的步骤与日志；
4. 成功后同步 Actions 自动提交到 `main` 的公开数据。

不要把“本地缺少 key”当作需要用户补配置的问题；这是仓库的预期架构。

## 常用远端验证入口

- `.github/workflows/weekly-update.yml`：完整周更新、热点重建、静态构建、Pages 部署与公开数据回写。
- `.github/workflows/rebuild-hotspot-network.yml`：只从云端缓存数据库重建热点网络。
- `.github/workflows/backfill-journals.yml`：按年份回填期刊、筛选、方法标注、热点重建与部署。
- `.github/workflows/ci.yml`：普通代码与前端构建检查。

手动测试优先使用工作流已有的 `workflow_dispatch`，不要为了触发运行而提交无意义的 YAML 改动。若工作流没有 `workflow_dispatch`，先明确设计合适的触发方式，再修改工作流。

## 数据产物

- `frontend/public/data/papers.json`、`all_papers.json` 和 `hotspots/` 是可提交的静态站数据产物。
- `frontend/public/data/hotspots/` 由 GitHub Actions 重建，不应手工编辑。
- Actions 使用默认 `GITHUB_TOKEN` 产生的提交不会递归触发其他工作流；负责写数据的工作流应自行完成校验和部署。

## 当前研究方法标签

`method` 当前为单选：`质性分析 / 量化分析 / 理论分析 / 综述 / 计算传播学`，不确定时为空。新论文在 AI 筛选时写入，旧论文用 `label-methods` 回填。
