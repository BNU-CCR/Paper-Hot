---
kind: build_system
name: 构建与发布流水线（Python 包 + Next.js 静态站点）
category: build_system
scope:
    - '**'
source_files:
    - pyproject.toml
    - frontend/package.json
    - frontend/next.config.mts
    - .github/workflows/ci.yml
    - .github/workflows/deploy-pages.yml
    - .github/workflows/weekly-update.yml
    - .github/workflows/refresh-hotspots.yml
    - backend/scripts/run_tracker.sh
    - backend/scripts/run_weekly.ps1
---

本项目采用双栈构建体系：后端以 Python 包 `journal-tracker` 为核心，通过 `pyproject.toml` + setuptools 构建；前端为基于 Next.js App Router 的静态站点，使用 pnpm 管理依赖并通过 `next build` 导出静态文件。两者通过 GitHub Actions 统一编排 CI、测试与部署流程。

**后端构建系统**
- 包定义与依赖：`pyproject.toml` 声明项目元数据、Python>=3.9 要求、运行时依赖（anthropic、pyyaml、requests）以及可选依赖组 `dev`（pytest、black、mypy）和 `analysis`（fastembed、numpy、scikit-learn、scipy、igraph）。
- 构建后端端点：`[project.scripts]` 暴露 `journal-tracker` CLI，指向 `journal_tracker.main:main`。
- 打包配置：setuptools 作为 build-backend，包发现范围限定在 `backend/` 目录下的 `journal_tracker*`。
- 代码质量：Black 行宽 100，Mypy 目标 Python 3.9，禁用未定义类型检查。

**前端构建系统**
- 包管理：`frontend/package.json` 使用 pnpm，Node 22，Next.js 16.2.12 + React 19。
- 构建脚本：`pnpm build` 调用 `next build`，输出到 `frontend/out/` 静态目录。
- 静态导出：`next.config.mts` 启用 `output: "export"`、`trailingSlash: true`，并根据 `GITHUB_ACTIONS` 环境变量设置 `basePath` 以适配 GitHub Pages。
- TypeScript：`tsconfig.json` 启用严格模式、模块解析为 bundler，路径别名 `@/*`。

**CI/CD 流水线（GitHub Actions）**
- `ci.yml`：对 main 分支 push 和 PR 触发，并行执行三个 job：
  - `python-tests`：在 Python 3.9 与 3.12 矩阵上安装包并运行 `unittest discover backend/tests`，随后执行 `journal-tracker workflow-status` 冒烟测试。
  - `analysis-tests`：安装 `[analysis]` 可选依赖，运行热点网络、验证与论文特征相关测试，并对空数据库执行 `build-hotspot-network` 与 `validate-hotspot-data` 冒烟测试。
  - `frontend-tests`：使用 pnpm v10 + Node 22 安装依赖并构建静态站点，校验 `frontend/out/` 下关键 HTML 与 JSON 文件存在。
- `deploy-pages.yml`：当 `frontend/**` 或自身文件变更时触发，构建 Next.js 站点并通过 `actions/deploy-pages@v4` 部署到 GitHub Pages。
- `weekly-update.yml`：每周一北京时间 13:00 定时触发，完整工作流包括：恢复缓存的 SQLite 数据库与 FastEmbed 模型 → 安装分析依赖 → 校验 `ANTHROPIC_API_KEY` → 执行 `weekly-run` → 构建热点网络 → 验证生成的 JSON 数据 → 构建静态站点 → 部署 GitHub Pages → 保存缓存 → 上传运行报告与公开数据工件 → 条件性提交并推送更新的公开数据到 main 分支。
- `refresh-hotspots.yml`：手动触发的月度热点刷新流程，生成热点数据后重新构建并部署站点。

**本地运行脚本**
- `backend/scripts/run_tracker.sh`：Linux/macOS 一键运行脚本，自动激活虚拟环境（优先 `.venv`），调用 `python -m journal_tracker.main "$@"`。
- `backend/scripts/run_weekly.ps1`：Windows PowerShell 脚本，封装 `weekly-run` 参数，支持日志记录、Git 提交与推送。
- `backend/scripts/register_weekly_task.ps1`：用于注册 Windows 计划任务。

**数据与产物约定**
- 后端工作数据库：`backend/data/papers.db`（SQLite），CI 中通过 actions/cache 持久化。
- 公开数据：`frontend/public/data/` 下的 `papers.json`、`all_papers.json`、`hotspots.json` 及 `hotspots/` 子目录（graph.json、manifest.json、trends.json），由 `readme_update` 模块生成并经 `json.tool` 校验。
- 构建产物：`frontend/out/` 为 Next.js 静态导出目录，直接部署至 GitHub Pages。

**约束与规范**
- Python 版本矩阵：CI 同时验证 3.9 与 3.12，确保向后兼容。
- 依赖锁定：前端使用 `--frozen-lockfile` 保证构建可重现。
- 环境变量：API Key（`ANTHROPIC_API_KEY`、`SEMANTIC_SCHOLAR_API_KEY`）通过 GitHub Secrets/Variables 注入，缺失时显式报错退出。
- 并发控制：各 workflow 通过 `concurrency` 组名避免重复运行冲突。