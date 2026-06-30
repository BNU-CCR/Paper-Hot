# Paper HOT 静态公开站第一版实现设计

日期：2026-05-20

## 背景

项目已经具备论文采集、AI 筛选、SQLite 存储、公开 JSON 导出能力。当前要实现的是第一版公开网站：不在网站上调用 Claude API，而是展示本地脚本已经 AI 筛选并导出的公开论文结果。

本设计延续既有视觉方案 `2026-05-10-paper-hot-public-site-design.md`：参考 AI HOT 的窄侧栏、双主题、顶部筛选面板、日期时间线、论文卡片、标签、分数、摘要和推荐理由，但转译为计算传播论文情报站。

## 第一版目标

实现一个纯静态网站，读取 `public/data/papers.json` 并渲染 AI 筛选后的论文信息。

第一版必须支持：

- AI HOT 风格的左侧窄侧栏与主内容区。
- `light`、`dark`、`system` 三段主题切换。
- 首页顶部筛选与搜索面板。
- 按 `High` / `Medium` / 全部筛选。
- 按标签筛选。
- 搜索标题、摘要、作者、期刊、标签。
- 时间线式论文卡片列表。
- 展示 AI 摘要、推荐理由、标签、分数和原文链接。

## 非目标

第一版不实现：

- 网站端调用 Claude API。
- 访客提交论文进行 AI 筛选。
- 私有后台、登录、权限系统。
- 周报页。
- 详情页路由。
- RSS / JSON Feed。
- 小红书分享卡片。
- 自动部署流水线。

这些功能放到后续阶段。

## 文件结构

新增静态前端目录：

```text
web/
├── index.html
├── styles.css
└── app.js
```

继续使用现有公开数据文件：

```text
public/data/papers.json
```

本地预览时从项目根目录启动静态服务器，使 `web/app.js` 可以读取 `../public/data/papers.json` 或等效相对路径。

## 数据输入

网站读取 `public/data/papers.json`，使用当前导出字段：

```json
{
  "id": 1,
  "title": "...",
  "authors": ["..."],
  "journal": "...",
  "published_date": "...",
  "relevance": "High",
  "score": 92,
  "summary": "...",
  "reason": "...",
  "tags": ["..."],
  "doi": "...",
  "source_url": "...",
  "detail_slug": "..."
}
```

第一版前端只消费这些公开字段，不读取 SQLite、Prompt、配置文件或任何密钥。

## 页面结构

### 侧栏

桌面端左侧固定窄侧栏，移动端折叠为顶部区域。

侧栏包含：

- Logo：建议使用 `Paper HOT` 或 `CC Paper HOT`。
- 主导航：精选论文、主题标签、关于。
- 底部主题切换：月亮 / 系统 / 太阳三段式控件。

第一版导航可以是页内锚点，不需要多页面路由。

### 主内容区

主内容区包含：

1. 顶部信息面板：
   - 标题：精选论文。
   - 副标题：AI 辅助整理的计算传播论文精选。
   - 筛选按钮：全部、High、Medium。
   - 搜索框。

2. 标签筛选区域：
   - 从论文 `tags` 自动聚合。
   - 点击标签后只显示包含该标签的论文。
   - 支持清除标签筛选。

3. 时间线论文流：
   - 按 `published_date` 降序展示。
   - 缺少日期时放在后面。
   - 每张卡片显示论文公开字段。

## 论文卡片

卡片显示：

- relevance 与 score 徽章，例如 `High 92`、`Medium 74`。
- 标题。
- 作者。
- 期刊与发表日期。
- AI 摘要 `summary`。
- 推荐理由 `reason`，使用浅绿色提示条。
- 标签列表。
- DOI 链接与 source_url 原文链接。

如果字段为空：

- `score` 为空时只显示 relevance。
- `summary` 为空时不显示摘要块。
- `reason` 为空时不显示推荐理由条。
- `doi` 为空时不显示 DOI 链接。
- `source_url` 为空时不显示原文链接。

## 交互逻辑

`app.js` 负责：

1. fetch 公开 JSON。
2. 保存原始论文数组。
3. 根据当前筛选状态计算可见论文：
   - relevance 筛选。
   - 标签筛选。
   - 搜索关键词筛选。
4. 渲染标签列表。
5. 渲染时间线论文卡片。
6. 保存主题偏好到 `localStorage`。
7. 在 `system` 模式下跟随 `prefers-color-scheme`。

搜索范围包括：

- title
- summary
- reason
- authors
- journal
- tags

## 视觉方向

继承既有视觉 spec：

- 浅色背景使用冷灰蓝。
- 卡片使用白色或半透明白，低对比边框和轻阴影。
- 深色背景使用深蓝黑渐变。
- cyan 用于品牌、选中态、时间线节点和链接。
- High 使用绿色，Medium 使用琥珀色。
- 推荐理由使用浅绿色提示条。
- 时间线使用淡灰竖线和 cyan/green 节点。

不直接复制 AI HOT 的品牌、文案或具体实现。

## 验证标准

实现完成后需要验证：

```bash
python -m src.main export-public
python -m http.server 8000
```

然后在浏览器中检查：

- 页面能加载公开 JSON。
- 至少能渲染当前测试论文。
- relevance 筛选可用。
- 标签筛选可用。
- 搜索可用。
- light / system / dark 主题切换可用。
- 空字段不会显示破碎 UI。
- 页面不读取或暴露配置文件、Prompt、API Key、Low 未发布论文和内部备注。

## 后续阶段

第一版完成后，再考虑：

1. 详情页和可分享单篇 URL。
2. 周报归档。
3. RSS / JSON feed。
4. 私有后台发布管理。
5. 自动部署。
6. 小红书分享卡片。
