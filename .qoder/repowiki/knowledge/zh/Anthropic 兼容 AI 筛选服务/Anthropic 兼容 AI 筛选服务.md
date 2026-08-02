---
kind: external_dependency
name: Anthropic 兼容 AI 筛选服务
slug: anthropic-deepseek
category: external_dependency
category_hints:
    - vendor_identity
    - auth_protocol
scope:
    - '**'
---

### Anthropic 兼容 AI 筛选服务
- 使用 Anthropic Claude API 兼容接口进行论文相关性筛选和内容摘要生成
- 默认配置指向 DeepSeek 的 Anthropic 兼容接口 (`https://api.deepseek.com/anthropic`)
- 通过 `ANTHROPIC_API_KEY` 环境变量注入认证信息，支持自定义 Base URL
- 当前模型配置为 `deepseek-v4-flash`，可灵活切换其他兼容模型
- 在每周工作流中对 pending 状态的论文进行批量 AI 筛选，输出 relevance、tags、summary
- 包含错误重试机制，失败的筛选结果会被标记并支持后续重筛
- 本地开发环境通过 `.local/key.env` 文件管理 API Key
- verify exact API/params against official docs