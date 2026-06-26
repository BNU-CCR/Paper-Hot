# 计算传播期刊追踪 / Paper HOT

面向计算传播研究的论文追踪与公开展示项目。目标是实现一个类似 AI HOT 的论文情报站：自动发现计算传播相关期刊论文，调用 AI 完成筛选、摘要、标签和推荐理由生成，再发布到公开网站，并在后续接入定期推送。

## 当前状态

目前已经跑通一条最小闭环：

- Semantic Scholar 论文发现。
- DeepSeek Anthropic-compatible API 论文筛选，输出 `High / Medium / Low`、摘要、标签和推荐理由。
- SQLite 本地存储与去重。
- 公开站 JSON 导出：`public/data/papers.json`。
- 静态公开站：`web/index.html` 读取 JSON 并展示论文流。
- CLI 发布管理：`publish`、`unpublish`、`publish-high`、`update-public`、`list-public`。
- 工作流体检与状态查看：`doctor`、`workflow-status`。
- 当前真实库状态：7 篇论文，其中 3 篇 High，公开站发布 2 篇真实 High 论文。
- 自动化测试覆盖配置、发现限流与临时错误重试、AI 响应解析、公开导出、通知开关和工作流命令。

尚未完成的核心部分：

- AI 筛选质量、推荐理由和标签体系优化。
- Semantic Scholar 采集日志、查询质量和关键词策略继续优化。
- 自动部署到公开 URL。
- 定期推送闭环。
- 私有后台或更方便的人工编辑入口。

## 目录结构

```text
.
├── config/
│   ├── journals.yaml
│   ├── prompts.yaml
│   └── settings.yaml
├── data/
│   └── papers.db              # 本地 SQLite 数据库，默认不提交
├── docs/
│   └── superpowers/
│       ├── specs/
│       └── plans/
├── public/
│   └── data/
│       └── papers.json        # 公开站读取的数据
├── scripts/
│   └── run_tracker.sh
├── src/
│   ├── config.py
│   ├── discovery.py
│   ├── filter.py
│   ├── main.py
│   ├── notification.py
│   ├── publication.py
│   └── storage.py
├── tests/
└── web/
    ├── index.html
    ├── app.js
    ├── styles.css
    └── app.test.cjs
```

## 安装

```bash
py -m pip install -e .
```

## 配置

本地密钥写入 `key.env`，不要提交到仓库。项目会读取 `.env` 或 `key.env`，这两个文件都已被 `.gitignore` 排除。

```env
ANTHROPIC_API_KEY=你的 DeepSeek API key
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
AI_MODEL=deepseek-v4-flash
SEMANTIC_SCHOLAR_API_KEY=你的 Semantic Scholar API key
SERVERCHAN_SCKEY=可选
```

说明：变量名仍保留 `ANTHROPIC_*`，是因为项目沿用 `anthropic` Python SDK，DeepSeek 提供 Anthropic API 格式兼容接口。

## 常用命令

完整采集、筛选、入库流程：

```bash
py -m src.main
```

查看环境配置：

```bash
py -m src.main doctor
```

查看工作流状态：

```bash
py -m src.main workflow-status
```

搜索论文但不入库：

```bash
py -m src.main search
```

列出本地论文：

```bash
py -m src.main list
```

发布管理：

```bash
py -m src.main publish <paper_id>
py -m src.main unpublish <paper_id>
py -m src.main publish-high
py -m src.main list-public
```

一键刷新公开站数据：

```bash
py -m src.main update-public
```

`update-public` 会先重筛之前 AI 筛选失败的论文，再公开所有 High 论文，并刷新 `public/data/papers.json`。如果没有筛选错误，不会调用 AI API。

导出数据：

```bash
py -m src.main export
py -m src.main export-public
```

本地预览公开站：

```bash
py -m http.server 8000
```

然后打开：

```text
http://127.0.0.1:8000/web/index.html
```

## 验证

Python 测试：

```bash
py -m unittest tests.test_config tests.test_publication tests.test_discovery tests.test_filter tests.test_notification -v
```

前端逻辑测试：

```bash
node web\app.test.cjs
```

当前最近一次验证结果：26 个 Python 测试通过，前端逻辑测试通过；真实 `search` 命令可返回 Semantic Scholar 结果。

## 近期路线

1. 稳定真实数据闭环：采集、筛选、入库、公开刷新。
2. 优化接口稳健性：采集报告、失败恢复、运行日志和关键词策略。
3. 优化 AI 筛选质量：更清晰的评分标准、推荐理由、标签体系。
4. 部署公开站：GitHub Pages / Vercel / Cloudflare Pages 任选其一。
5. 加入推送：周报、RSS、Server 酱或邮件。
6. 增加私有编辑入口：人工调整标题、摘要、标签、公开状态和 score。
