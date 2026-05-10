# 计算传播论文追踪系统 - Claude Code 使用指引

## 项目概述

这是一个用于自动追踪计算传播学领域论文的系统。使用 Claude Code 直接驱动工作流，无需 Make.com 等第三方服务。

## 系统架构

```
Claude Code (调度中心)
    ├→ asta-skill (论文发现/搜索 via MCP)
    ├→ Claude API (AI筛选)
    ├→ SQLite (本地存储)
    └→ 通知推送 (微信/邮件)
```

## 可用命令

### 1. 检查新论文
```
"检查新论文" 或 "运行论文追踪"
```
运行完整的论文发现 → AI筛选 → 存储 → 通知流程。

### 2. 搜索论文
```
"搜索计算传播相关论文"
"查找关于 [主题] 的论文"
```
直接调用 asta-skill 搜索论文。

### 3. 查看统计
```
"查看论文统计"
"显示追踪统计"
```
查看已追踪论文的数量和分布。

### 4. 添加期刊
```
"添加期刊 [期刊名]"
```
更新 config/journals.yaml 配置文件。

### 5. 导出论文
```
"导出论文到 CSV"
"导出 High 相关论文"
```
将论文导出为 CSV 格式。

### 6. 导出公开数据
```
"导出公开数据"
```
将已发布论文导出为公开站 JSON 数据。

### 7. 发布论文
```
"发布论文 [ID]"
"取消发布论文 [ID]"
"查看已发布论文"
```
管理公开站中可见的论文。

### 8. 查看待读论文
```
"显示待读论文"
"查看 High 相关论文"
```
从本地数据库查询并显示论文列表。

## 项目结构

```
期刊追踪/
├── src/
│   ├── __init__.py
│   ├── main.py              # 主入口
│   ├── discovery.py         # 论文发现 (Semantic Scholar API)
│   ├── filter.py            # AI筛选 (Claude API)
│   ├── storage.py           # SQLite存储
│   ├── notification.py     # 通知推送
│   └── config.py            # 配置管理
├── config/
│   ├── journals.yaml        # 期刊配置
│   ├── prompts.yaml         # AI Prompt
│   └── settings.yaml        # 全局设置
├── data/
│   └── papers.db            # SQLite数据库
├── public/
│   └── data/
│       └── papers.json      # 公开站数据导出
├── scripts/
│   └── run_tracker.sh       # 定时任务脚本
├── tests/
│   ├── test_config.py
│   └── test_publication.py
└── pyproject.toml
```

## 模块说明

### src.discovery.PaperDiscovery
论文发现模块，支持：
- `search_papers(query, year, limit)` - 关键词搜索
- `search_by_journal(journal, year, limit)` - 按期刊搜索
- `search_recent_papers(keywords, days, limit)` - 搜索最近论文
- `get_paper_by_doi(doi)` - 通过DOI获取论文
- `get_paper_citations(paper_id, limit)` - 获取引用列表

### src.filter.PaperFilter
AI筛选模块，使用Claude API判断论文相关性：
- `filter_paper(title, abstract, authors, journal)` - 筛选单篇论文
- 返回: `{relevance: "High/Medium/Low", reason, tags, summary}`

### src.storage.PaperStorage
本地存储模块（SQLite）：
- `add_paper(paper)` - 添加论文
- `paper_exists(link, doi)` - 检查重复
- `get_papers(relevance, status, limit)` - 获取论文列表
- `get_public_papers(limit)` - 获取已发布论文
- `get_statistics()` - 获取统计信息
- `export_to_csv(filepath, relevance)` - 导出CSV
- `set_paper_publication(paper_id, is_public)` - 设置公开发布状态

### src.notification.NotificationSender
通知推送模块：
- `send_paper_notification(paper)` - 发送单篇论文通知
- `send_batch_notification(papers)` - 发送批量通知

## AI筛选标准

系统使用预设的Prompt判断论文是否属于计算传播领域：

**纳入标准**（满足任一）：
- 选题相关：AI/ML、社交媒体、算法推荐、社交网络等
- 方法相关：NLP、网络分析、机器学习、大数据等
- AI特别条款：大模型相关研究，即使方法传统也纳入

**排除标准**：
- 纯理论/哲学思辨
- 纯批判性分析
- 传统问卷调查

**输出**：
- High: 明确是计算传播研究
- Medium: 边缘相关
- Low: 不相关

## 配置说明

### 环境变量
```bash
ANTHROPIC_API_KEY=sk-...        # Claude API密钥
SERVERCHAN_SCKEY=...            # Server酱密钥（可选）
```

### 期刊配置 (config/journals.yaml)
定义追踪的期刊列表和搜索关键词。

### 全局设置 (config/settings.yaml)
- API配置
- 通知配置
- 追踪参数

## MCP 工具使用

系统集成 asta-skill 作为 MCP 工具，提供：
- 论文检索（按关键词、标题、作者）
- 论文查询（DOI、arXiv、PMID）
- 引用遍历
- 批量查询
- 片段搜索（约500词）

在 Claude Code 会话中，可以直接用自然语言调用这些功能。

## 定时任务

使用 Claude Code 的 CronCreate 功能设置定时提醒：
```bash
/cron
```
选择"定时提醒"，设置每天固定时间提醒你运行论文追踪。

## 扩展功能

- [ ] 飞书集成（替代SQLite）
- [ ] 更多通知渠道
- [ ] 引用追踪增强
- [ ] 更多期刊
- [ ] PDF全文分析

## 故障排除

**API Key 未设置**
```
Error: ANTHROPIC_API_KEY is required
```
设置环境变量或更新 config/settings.yaml

**搜索无结果**
- 检查网络连接
- 尝试不同的关键词
- 确认 Semantic Scholar API 可用

**数据库错误**
- 检查 data/ 目录是否存在
- 确认写入权限
