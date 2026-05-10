# 项目架构审视进度

## 2026-05-10

- 用户提出从更高维度审视当前项目架构、文件结构、Git/GitHub 流程、部署和开发顺序。
- 创建 `task_plan.md`、`findings.md`、`progress.md` 用于跟踪本次审视。
- 盘点了核心代码、配置、数据库结构、依赖和安全提交风险。
- 验证 `python -m src.main stats` 可运行，当前数据库有 1 条测试论文。
- 论文搜索命令在沙箱内被网络权限阻止，联网验证申请被审批系统拒绝，记录为尚未跑通。
- 开始第一批工程化重构：新增 `.gitignore`、测试目录、公开数据导出模块。
- 将配置真正接入发现与筛选流程：增加 `semantic_scholar_api_key`、`claude_model`、Prompt 访问器和发现关键词聚合。
- 扩展 `papers` 表字段以支持发布：新增 `score`、`is_public`，并加入旧库兼容迁移逻辑。
- 新增 `export-public` 命令，导出 `public/data/papers.json`。
- 使用 `unittest` 验证配置读取和公开导出行为，测试通过。
