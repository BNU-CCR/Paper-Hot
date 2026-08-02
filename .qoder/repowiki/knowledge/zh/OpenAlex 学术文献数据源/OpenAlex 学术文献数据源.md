---
kind: external_dependency
name: OpenAlex 学术文献数据源
slug: openalex
category: external_dependency
category_hints:
    - vendor_identity
    - sdk_real_api
scope:
    - '**'
---

### OpenAlex 学术文献数据源
- 作为红榜期刊论文抓取的主要数据源，通过 `OpenAlexDiscovery` 类调用 `https://api.openalex.org` 接口
- 支持按 source id 或 ISSN 过滤期刊更新，使用 `/works` 端点获取论文元数据
- 关键字段包括 topics、keywords、referenced_works、cited_by_count、is_retracted 等用于热点分析
- 无 API key 要求但可通过配置 `openalex_api_key` 提升请求限制
- 与 Crossref DOI 覆盖验证配合使用，确保数据完整性
- 每周工作流中自动回填缺失的 features 数据（topics/keywords/references/citations）
- 降级策略：当 OpenAlex 数据缺失时，系统优雅降级为仅使用 title + abstract 进行 embedding
- verify exact API/params against official docs