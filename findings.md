# 项目架构审视发现

## 已确认背景

- 目标是将论文追踪项目发展为公开部署的 AI 自动论文情报应用。
- 公开端只展示筛选后的论文结果，不公开筛选机制、配置和内部数据。
- 当前已形成设计 spec：`docs/superpowers/specs/2026-05-10-paper-hot-public-site-design.md`。

## 待补充

- 当前代码模块职责。
- 当前数据库字段与公开数据字段差距。
- 当前采集链路可运行性。
- 版本控制和部署准备情况。

## 2026-05-10 架构盘点

### 当前模块

- `src/main.py`：命令行入口，提供完整流程、搜索、统计、导出 CSV。
- `src/discovery.py`：论文发现模块，当前通过 Semantic Scholar API 搜索论文。
- `src/filter.py`：Claude API 筛选模块，硬编码了筛选 Prompt 和模型名。
- `src/storage.py`：SQLite 存储模块，表结构为单表 `papers`。
- `src/notification.py`：通知模块，支持 Server 酱和占位邮件通知。
- `src/config.py`：读取 `config/*.yaml` 和环境变量。
- `config/journals.yaml`：期刊与关键词配置。
- `config/settings.yaml`：API、通知、追踪和日志配置。

### 当前可用性

- `python -m src.main stats` 可运行，当前数据库有 1 条测试论文。
- Python 依赖可导入：`anthropic`、`requests`、`yaml`。
- 当前环境变量未设置 `ANTHROPIC_API_KEY`、`SERVERCHAN_SCKEY`。
- `python -m src.main search` 在当前沙箱内被网络权限阻止；已申请联网验证但审批系统拒绝，因此实际论文获取链路尚未验证成功。

### 主要缺口

- 当前目录不是 Git 仓库。
- 没有 `.gitignore`，存在不应提交的 `__pycache__`、`data/papers.db`、`.claude/settings.local.json`。
- 没有测试目录。
- 采集配置没有真正贯通：`Config` 能读取 `journals.yaml`，但 `PaperDiscovery.search_recent_papers()` 默认仍使用类内置关键词。
- `config/settings.yaml` 中的 `semantic_scholar_api_key` 没有传入 `PaperDiscovery`。
- `search_recent_papers(days=7)` 参数目前没有实际用于按日期过滤。
- `filter.py` 里 Prompt 和模型名硬编码，`config/prompts.yaml` 与 `config/settings.yaml` 没有真正驱动筛选。
- 数据库字段不足以直接支持公开站：缺少 `score`、`published/publication` 状态、`slug`、`source`、`public_notes`、`last_seen_at` 等发布字段。
- 当前 CSV 导出不能满足公开站 JSON 数据源需求。

### 初步判断

- 现有代码可以作为采集/筛选原型保留。
- 不建议推倒重写。
- 需要先做工程化整理、版本控制、采集验证和数据模型扩展，再进入公开前端实现。

## 2026-05-10 第一批工程化改造

### 已完成

- 新增 `.gitignore`，排除数据库、缓存、本地设置和 `.superpowers/`。
- 新增 `tests/`，使用标准库 `unittest`，避免依赖本地未安装的 `pytest`。
- `Config` 现在可读取：
  - `semantic_scholar_api_key`
  - `claude_model`
  - `filter_system_prompt`
  - `filter_user_template`
  - 合并后的发现关键词 `get_discovery_keywords()`
- `PaperDiscovery` 现在会读取配置里的 Semantic Scholar key 和发现关键词。
- `PaperFilter` 现在会读取配置里的模型名和 Prompt，而不是完全硬编码。
- `PaperStorage` 新增字段：
  - `score`
  - `is_public`
- `PaperStorage` 增加旧库字段补齐逻辑，避免已有 `papers.db` 无法直接升级。
- 新增 `src/publication.py` 与 `python -m src.main export-public`，导出公开 JSON。

### 当前状态

- `public/data/papers.json` 已能生成。
- 当前导出结果是空数组 `[]`，因为数据库里现有测试论文没有被标记为 `is_public=1`。
- 这符合当前发布设计，但也说明下一步需要补“发布管理”动作或脚本。
