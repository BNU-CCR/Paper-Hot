---
kind: external_dependency
name: Semantic Scholar 学术论文搜索引擎
slug: semantic-scholar
category: external_dependency
category_hints:
    - vendor_identity
    - auth_protocol
scope:
    - '**'
---

### Semantic Scholar 学术论文搜索引擎
- 作为补充论文发现渠道，提供基于关键词和期刊的论文搜索功能
- 通过 `PaperDiscovery` 类调用 `https://api.semanticscholar.org/graph/v1` 接口
- 需要可选的 `SEMANTIC_SCHOLAR_API_KEY` 环境变量提高请求限制
- 支持 `/paper/search`、`/paper/{id}`、`/paper/{id}/citations` 等端点
- 主要用于计算传播领域相关论文的发现和引用关系获取
- 与 OpenAlex 形成互补：OpenAlex 负责期刊定向抓取，Semantic Scholar 负责主题探索
- 包含完整的重试机制和限流处理（429/500/502/503/504 错误码）
- verify exact API/params against official docs