---
kind: dependency_management
name: Python 与前端依赖管理（pyproject.toml + pnpm）
category: dependency_management
scope:
    - '**'
source_files:
    - pyproject.toml
    - frontend/package.json
    - frontend/pnpm-lock.yaml
    - backend/journal_tracker.egg-info/requires.txt
---

本仓库采用双语言栈，依赖管理分为 Python 后端与 Next.js 前端两部分，分别使用不同的包管理器与锁定策略。

**Python 后端（journal-tracker）**
- 使用 `pyproject.toml` 作为唯一依赖声明入口，通过 setuptools 构建系统安装。
- 运行时依赖：`anthropic>=0.18.0`、`pyyaml>=6.0`、`requests>=2.28.0`。
- 可选依赖分组：`dev`（pytest、pytest-asyncio、black、mypy）和 `analysis`（fastembed、numpy、scikit-learn、scipy、igraph），通过 `pip install .[dev|analysis]` 按需安装。
- 未使用 Poetry、Pipenv 或 requirements.txt；`backend/journal_tracker.egg-info/requires.txt` 为 setuptools 自动生成的元数据文件，非手动维护的锁文件。
- 无 Python 虚拟环境锁定文件（如 `poetry.lock`、`requirements.lock`），依赖版本以 `>=` 宽松约束为主，仅分析组使用 `<` 上限约束。
- 包名 `journal-tracker`，CLI 入口通过 `[project.scripts]` 暴露 `journal-tracker` 命令。

**Next.js 前端（frontend/）**
- 使用 `pnpm` 作为包管理器，`package.json` 声明依赖，`pnpm-lock.yaml` 锁定精确版本。
- 核心依赖：Next.js 16.2.12、React 19.2.8、Radix UI 组件库、Tailwind CSS v4、graphology/sigma 用于网络可视化、zod 用于类型校验。
- 开发依赖与生产依赖严格分离，包含 TypeScript 类型定义与 Tailwind PostCSS 插件。
- 使用 `pnpm-workspace.yaml` 表明支持多包工作区（当前仅单包）。
- 依赖更新通过 `pnpm update` 管理，lockfile 提交至版本控制以保证可重现构建。

**环境与工具链约定**
- Python 要求 `>=3.9`，由 `requires-python` 字段强制。
- Black 配置行长度 100，目标 Python 版本覆盖 3.9–3.11。
- mypy 启用 `warn_return_any` 与 `warn_unused_configs`，但允许未标注类型的函数定义。
- 前端通过 `next.config.mts` 与 `postcss.config.mjs` 管理构建管线，TypeScript 编译输出到 `tsconfig.tsbuildinfo`。

**未发现的实践**
- 无私有 PyPI 镜像或 GOPRIVATE 等私有源配置。
- 无依赖安全扫描（如 pip-audit、npm audit）在 CI 中显式配置。
- 无 vendoring（如 pip download --no-deps 或 go mod vendor）策略。