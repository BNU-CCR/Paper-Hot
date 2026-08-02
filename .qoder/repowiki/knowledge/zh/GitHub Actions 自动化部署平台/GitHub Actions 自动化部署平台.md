---
kind: external_dependency
name: GitHub Actions 自动化部署平台
slug: github-actions
category: external_dependency
category_hints:
    - vendor_identity
    - framework_behavior
scope:
    - '**'
---

### GitHub Actions 自动化部署平台
- 运行每周一次的论文更新工作流（每周一 13:00 GMT+8），支持手动触发
- 包含 Python 测试套件执行、数据库缓存恢复、静态网站构建和部署
- 通过 repository secrets 管理敏感信息（ANTHROPIC_API_KEY、SEMANTIC_SCHOLAR_API_KEY）
- 使用 GitHub Pages 发布静态网站，支持版本控制和回滚
- 工作流产物包括：更新的数据库、生成的 JSON 数据、运行报告、网站构建产物
- 支持增量更新：仅在公共数据发生变化时提交到 main 分支
- 内置健康检查：验证生成的 JSON 文件格式正确性
- 缓存策略：SQLite 数据库和 FastEmbed 模型缓存跨运行持久化