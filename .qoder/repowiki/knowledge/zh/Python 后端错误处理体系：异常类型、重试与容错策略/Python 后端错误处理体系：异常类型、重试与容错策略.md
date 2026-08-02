---
kind: error_handling
name: Python 后端错误处理体系：异常类型、重试与容错策略
category: error_handling
scope:
    - '**'
source_files:
    - backend/journal_tracker/main.py
    - backend/journal_tracker/discovery.py
    - backend/journal_tracker/coverage.py
    - backend/journal_tracker/storage.py
    - backend/journal_tracker/hotspot_network.py
    - backend/journal_tracker/hotspot_validation.py
    - backend/journal_tracker/notification.py
---

## 1. 使用的系统与模式
- Python 原生异常体系为主，辅以少量自定义异常类（`NoHotspotCandidatesError`、`HotspotValidationError`）。
- 对外部 API 调用统一采用「带指数退避的重试 + 可重试状态码判断」模式，失败时抛出 `requests.RequestException`/`HTTPError`，由上层捕获或记录。
- 工作流层通过 try/except 包裹易错步骤，将单次失败降级为「标记错误并继续」，保证批处理不中断。
- CLI 入口对关键子命令做显式异常分支处理，区分「可跳过」和「应退出非零码」两类错误。

## 2. 核心文件与位置
- 异常定义与传播
  - `backend/journal_tracker/hotspot_network.py`：定义 `NoHotspotCandidatesError(ValueError)` 并在热点候选为空时抛出；多处使用 `ValueError` 表达参数/数据校验失败。
  - `backend/journal_tracker/hotspot_validation.py`：定义 `HotspotValidationError(ValueError)`，用于静态热点数据校验失败。
- 外部请求与重试
  - `backend/journal_tracker/discovery.py`：`PaperDiscovery._get_json`、`OpenAlexDiscovery._get_json` 实现统一的 3 次重试、429/5xx 判定、Retry-After 优先的指数退避；网络异常以 `requests.RequestException` 上抛。
  - `backend/journal_tracker/coverage.py`：`CrossrefClient._get_json` 同样实现重试与退避，失败时抛出 `requests.RequestException`。
- 工作流容错与错误记录
  - `backend/journal_tracker/main.py`：在筛选、回填等循环中用 `try/except Exception` 捕获错误，调用 `storage.mark_filter_error` 将论文标记为 `screening_status='error'`，并打印日志后 continue，避免单条失败阻塞整批。
  - `backend/journal_tracker/storage.py`：提供 `mark_filter_error` 方法，把错误信息写入 reason 字段并更新 screening_status，供后续重筛流程消费。
- 通知与输出
  - `backend/journal_tracker/notification.py`：发送失败仅打印日志并返回 False，不影响主流程；未配置项直接跳过而非抛错。

## 3. 架构与约定
- 异常分类
  - 参数/数据校验失败：统一使用 `ValueError`（如缺少 API Key、AI 响应无法解析、维度不匹配、JSON 结构不符等），便于调用方按语义快速定位。
  - 业务条件性失败：热点网络构建无候选时使用自定义 `NoHotspotCandidatesError`，CLI 层将其视为「本次无需生成网络」而优雅跳过（exit 0）。
  - 数据完整性校验失败：热点数据验证模块使用 `HotspotValidationError`，CLI 层据此决定 exit code 0/1。
- 外部依赖容错
  - 所有 HTTP 客户端均封装 `_get_json`，遵循相同重试策略：最多 3 次，针对 429/500/502/503/504 进行指数退避，优先读取 Retry-After 头；最终仍失败则向上抛出异常。
  - 批量抓取过程中，单个期刊/关键词失败仅计入报告中的 `failed_queries` 与 `errors` 列表，不中断整体流程。
- 工作流级容错
  - AI 筛选、OpenAlex 回填等长任务采用「逐条 try/except」模式，失败记录到数据库的 error 状态，支持 `refilter-errors` 命令重跑。
  - 统计与报告始终产出，即使部分步骤失败也会包含 errors 摘要，便于 CI 与人工巡检。
- CLI 错误码约定
  - 成功路径返回 0；需要终止的错误（如 doctor 检查失败、validate-hotspot-data 校验失败）通过 `sys.exit(非0)` 表达；可跳过场景（如无热点候选）也返回 0。

## 4. 约定与约束
- 对外部 API 调用必须走封装好的 `_get_json`，禁止裸 `requests.get`，以确保重试与退避策略一致。
- 业务校验失败一律抛 `ValueError`，不要吞掉异常或使用返回值表示错误。
- 批处理中不可让单条失败导致整个批次中断；应捕获异常、记录错误状态、继续处理剩余条目。
- 自定义异常需继承自 `ValueError`，以便上层可用统一的 except ValueError 捕获并给出友好提示。
- 通知类操作失败不得影响主流程，只能记录日志并返回布尔值。
- 所有可观测性信息（运行报告、覆盖率报告、weekly_run 报告）必须包含 errors 字段，且至少保留最近 5 条错误摘要。