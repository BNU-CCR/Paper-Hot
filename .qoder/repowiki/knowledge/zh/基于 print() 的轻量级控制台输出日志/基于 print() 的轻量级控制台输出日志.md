---
kind: logging_system
name: 基于 print() 的轻量级控制台输出日志
category: logging_system
scope:
    - '**'
source_files:
    - backend/journal_tracker/main.py
    - backend/journal_tracker/discovery.py
    - backend/journal_tracker/filter.py
    - backend/journal_tracker/hotspot_network.py
---

本仓库未引入任何专用日志框架（如 logging、loguru、structlog 等），后端所有模块统一使用 Python 内置的 `print()` 函数进行控制台输出，作为唯一的“日志系统”。

**系统与工具**
- 仅依赖标准库 `print()`，无任何第三方日志库导入。
- 在 Windows 非 UTF-8 终端下通过 `main.py` 中的 `safe_print()` 包装器处理编码问题，避免特殊字符打印失败。

**关键文件与位置**
- `backend/journal_tracker/main.py`：CLI 入口，集中了大量进度/统计/状态类的 `print()` 输出，并提供 `safe_print()` 辅助函数。
- `backend/journal_tracker/discovery.py`：OpenAlex/Semantic Scholar 发现流程中的错误信息通过 `print(f"搜索论文时出错: {e}")` 等形式输出。
- `backend/journal_tracker/filter.py`：AI 筛选异常以 `print(f"筛选论文 ... 时出错: {e}")` 形式输出。
- `backend/journal_tracker/hotspot_network.py`：热点网络构建流水线使用大量带步骤编号的 `print("[1/9] ...")` 风格进度输出。
- `backend/journal_tracker/storage.py`、`notification.py`、`publication.py` 等模块中未发现独立日志调用，主要业务逻辑不直接输出日志。

**架构与约定**
- 无统一的 logger 实例或日志级别配置；每个模块自行决定何时 `print()`。
- 输出内容以人类可读的中文提示为主，包含步骤编号、计数、错误堆栈片段等信息，便于交互式运行和 CI 观察。
- 结构化输出并非通过日志框架实现，而是通过 JSON 报告文件（如 `weekly_run_*.json`、`coverage_latest.json`）持久化到 `config.data_dir/reports/` 目录，供外部消费。

**约定与约束**
- 代码中不存在 `import logging`、`from logging`、`logging.config`、`logger =` 等日志框架初始化模式，表明本项目刻意未采用结构化日志方案。
- 所有可观测性均通过 `print()` 控制台输出 + JSON 报告文件组合实现，没有日志轮转、分级过滤、多 sink 路由等机制。
- 跨平台兼容性通过 `safe_print()` 统一处理编码，是本项目对 `print()` 输出的唯一规范化约束。