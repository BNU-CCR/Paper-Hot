# 计算传播论文追踪

一个面向计算传播研究的论文追踪项目。当前阶段的目标是把“本地脚本原型”整理成可版本控制、可验证、可扩展、后续可公开部署的论文情报应用。

## 当前状态

目前项目已经具备这些能力：

- 使用 Semantic Scholar API 搜索论文。
- 使用 Claude API 为论文生成 `High / Medium / Low` 相关性判断、摘要、推荐理由和标签。
- 将结果存入本地 SQLite 数据库。
- 导出 CSV。
- 导出公开站使用的 JSON 数据文件。

目前还没有完成这些部分：

- 真实联网环境下的论文获取验证。
- 论文“公开发布”管理流程。
- 公开前端 UI。
- 自动部署和 GitHub Actions。

## 当前目录结构

```text
.
├── config/
│   ├── journals.yaml         # 期刊和关键词配置
│   ├── prompts.yaml          # AI 筛选 Prompt 配置
│   └── settings.yaml         # 全局设置
├── data/
│   └── papers.db             # 本地 SQLite 数据库（默认不提交）
├── docs/
│   └── superpowers/specs/    # 设计文档
├── public/
│   └── data/
│       └── papers.json       # 公开站数据导出
├── scripts/
│   └── run_tracker.sh        # 定时运行脚本
├── src/
│   ├── config.py             # 配置读取
│   ├── discovery.py          # 论文发现
│   ├── filter.py             # AI 筛选
│   ├── main.py               # CLI 入口
│   ├── notification.py       # 通知发送
│   ├── publication.py        # 公开数据导出
│   └── storage.py            # SQLite 存储
├── tests/
│   ├── test_config.py
│   └── test_publication.py
├── CLAUDE.md
├── findings.md
├── progress.md
├── task_plan.md
└── pyproject.toml
```

## 环境要求

- Python 3.9+
- `anthropic`
- `pyyaml`
- `requests`

安装依赖：

```bash
pip install -e .
```

## 配置

建议通过环境变量注入密钥，不要写入仓库文件。

```bash
ANTHROPIC_API_KEY=...
SEMANTIC_SCHOLAR_API_KEY=...
SERVERCHAN_SCKEY=...
```

配置文件：

- `config/journals.yaml`
  - 维护期刊、关键词和全局发现关键词。
- `config/prompts.yaml`
  - 维护筛选 `system prompt` 和 `user template`。
- `config/settings.yaml`
  - 维护模型名、通知配置、追踪参数等。

## 命令行用法

完整流程：

```bash
python -m src.main
```

搜索论文：

```bash
python -m src.main search
```

查看统计：

```bash
python -m src.main stats
```

导出 CSV：

```bash
python -m src.main export
```

导出公开站 JSON：

```bash
python -m src.main export-public
```

发布论文到公开站：

```bash
python -m src.main publish <paper_id>
python -m src.main unpublish <paper_id>
python -m src.main list-public
```

## 数据模型

当前 `papers` 表核心字段包括：

- 论文元信息：`title`、`authors`、`journal`、`published_date`、`link`、`doi`
- AI 筛选结果：`relevance`、`reason`、`tags`、`summary`
- 发布相关：`score`、`is_public`
- 本地管理：`status`、`created_at`、`updated_at`

说明：

- `is_public = 1` 的论文才会进入 `public/data/papers.json`
- 当前项目还没有单独的发布管理界面，但已经有最小命令行发布管理能力

## 验证

当前已落地的本地验证命令：

```bash
python -m unittest tests.test_config tests.test_publication -v
python -m src.main stats
python -m src.main export-public
```

说明：

- 这些命令验证配置读取、公开数据导出和 CLI 基础行为。
- 论文搜索是否能真正拿回线上数据，仍取决于本机网络权限和 API 可达性。

## GitHub 准备情况

当前仓库已经做了基础整理：

- 已添加 `.gitignore`
- 已移除 `__pycache__`、临时预览文件和重复 Prompt 文档
- `data/*.db`、`.claude/settings.local.json`、`.superpowers/` 默认不会进入版本控制

建议：

- GitHub 仓库先设为私有
- 在真实采集链路跑通、公开站上线前，再决定是否开源

## 当前进展

截至现在，已经完成：

- 项目结构初步工程化
- 配置与代码解耦的第一轮整理
- 公开 JSON 导出模块
- 基础测试
- 公开站设计 spec

还未完成：

- 跑通真实论文获取
- 设计并实现“发布管理”
- 构建公开前端
- 部署与自动更新

## 近期路线

建议按这个顺序继续：

1. 初始化 Git 仓库并推送到 GitHub 私有仓库。
2. 在真实网络环境下验证 `search`。
3. 增加“设置论文为公开发布”的命令或脚本。
4. 固定公开 JSON 字段结构。
5. 再开始公开前端 UI。
