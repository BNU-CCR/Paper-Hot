---
kind: configuration_system
name: 基于 YAML + .env 分层加载的论文追踪系统配置管理
category: configuration_system
scope:
    - '**'
source_files:
    - backend/journal_tracker/config.py
    - backend/config/settings.yaml
    - backend/config/journals.yaml
    - backend/config/prompts.yaml
    - backend/config/topic_overrides.yaml
    - pyproject.toml
---

该仓库采用集中式 YAML 配置文件与本地环境变量相结合的分层配置体系，由 `backend/journal_tracker/config.py` 中的 `Config` 类统一加载和管理。配置系统按以下层次组织：

**1. 配置文件结构**
- `backend/config/settings.yaml`：全局运行时设置（API Key、数据库路径、通知开关、定时任务、日志级别、热点网络参数等）
- `backend/config/journals.yaml`：期刊追踪清单，包含期刊元数据、优先级（core/watch/skip）、OpenAlex ID、ISSN、关键词等
- `backend/config/prompts.yaml`：AI 筛选与热点归纳的 system prompt 和 user template，以及允许标签列表
- `backend/config/topic_overrides.yaml`：主题人工重命名与合并规则，用于覆盖 LLM 生成的主题名称

**2. 敏感信息加载策略**
通过 `_load_env_file()` 方法按优先级查找 `.env`、`key.env`、`.local/key.env` 三个文件，解析键值对后与环境变量 `os.environ` 及 `settings.yaml` 形成三级回退机制。所有 API Key（ANTHROPIC_API_KEY、OPENALEX_API_KEY、SEMANTIC_SCHOLAR_API_KEY 等）均优先从环境变量获取，确保密钥不入库。

**3. 配置访问模式**
- 通过 `get_config()` 单例函数获取全局配置实例
- 使用属性访问器（如 `anthropic_api_key`、`database_path`、`hotspot_network_config`）提供类型安全的配置读取
- 提供业务方法如 `get_tracked_journals()`、`get_discovery_keywords()` 封装配置查询逻辑

**4. 路径解析约定**
- 相对路径自动解析为相对于 backend 根目录的路径
- 公开数据导出目录固定为 `frontend/public/data`
- 数据库默认路径为 `data/papers.db`，支持绝对路径覆盖

**5. 依赖声明**
在 `pyproject.toml` 中声明 `pyyaml>=6.0` 作为唯一配置解析依赖，项目脚本入口 `journal-tracker = "journal_tracker.main:main"` 暴露 CLI 命令。