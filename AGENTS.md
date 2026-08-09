# Paper HOT 设计规范（Codex + Claude 共用）

Codex 与 Claude Code 都会自动读取仓库根目录的 `AGENTS.md`。工作前还应按任务范围阅读：

- `CLAUDE.md`：当前产品方向、数据管线、方法标签与云端工作流约定。
- `README.md`、`docs/project-map.md`、`docs/roadmap.md`：项目状态、目录职责与待办。

## 前端技术栈

- 前端为 Next.js 16 App Router + React 19，**全部组件用 TypeScript**（`.tsx` / `.ts`，`strict: true`）。新代码不要写 `.js` 文件。
- 样式基于 **Tailwind CSS v4** utilities；颜色/圆角等 token 通过 `app/globals.css` 顶部的 `@theme inline` 映射到 CSS 变量（`--background`、`--primary`、`--radius` 等），不要在组件里写死颜色。布局与纸卡等复杂样式保留在 `app/*.css` 的普通 CSS 规则中。
- **数据获取 RSC-first**：静态站点在构建时用 `frontend/lib/data.ts` 读 `public/data/*.json`，由 server component 预渲染进 HTML；交互部分拆成 client component（`"use client"`）接收 props。不要在新代码里用 client `useEffect` fetch 数据。
- 主题切换沿用 `data-theme` + CSS 变量；Tailwind 的 `dark:` 变体已绑定到 `[data-theme="dark"]`。

## 设计体系

- 组件库为 shadcn/ui 风格：Radix primitives + Tailwind utilities，包装组件在 `frontend/components/ui/`，类名用 `cn()` 合并。
- 新增或改造 UI 前，先对照一轮 shadcn/ui 官方对应组件的结构、间距、状态与交互样式，再结合本项目 token 调整，不凭空另造一套视觉语言。
- 图标统一用 `lucide-react`，尺寸 14–16px；装饰性图标加 `aria-hidden="true"`。
- 标题用衬线（Georgia / "Noto Serif SC" / "Songti SC"），正文用系统无衬线；颜色、圆角、间距沿用现有 CSS 变量（`--radius`、`--border`、`--muted-foreground` 等），不写死值。
- 亮/暗主题通过 `data-theme` + CSS 变量切换，不要硬编码颜色。
- 布局：左侧固定 `sidebar`（224px）+ `main` 内容区；页面级 hero 直接用 `h1`；工具条放 `.toolbar` / `.library-toolbar`（`shadcn-controls`）。

## 标题与标签：一个区块只保留一个标题

- 每个 section 只保留一个语义标题（h2/h3）。
- 尽量不要使用 `.eyebrow` 小标签：页面顶部不放装饰性小字（如“期刊目录”“LLM 月度聚合”“ABOUT PAPER HOT”“期刊精读”），也不要 eyebrow + 标题成对表达同一语义（如“按主题浏览 / 主题标签”“期刊论文 / 论文列表”）。
- 数量、日期等元信息放标题右侧的 `.count` 等辅助元素，不要另起小标题。

## 不要占位提示

- 不要在页面或功能底部放置常驻的解释性提示文本（例如“点击标签筛选论文，再次点击可取消”）。需要说明时用真实状态或空状态表达，而不是 hint 段落。
- 状态反馈只在状态真实存在时渲染（如筛选生效时显示“当前筛选 …”状态条）。
- 空状态（`.empty-state`）只在确实无数据时出现，文案给出可执行动作。

## 交互控件

- 卡片 hover 不使用上浮、位移或抬升阴影特效；需要强调可点击性时，仅使用克制的边框或背景状态。
- 卡片 hover 描边使用柔和灰色（`--border` / `--muted-foreground` 混合），不要变成接近黑色的高对比描边。
- 二选一/多选一切换用 Tabs（`TabsList`/`TabsTrigger`），不要用普通 Button 模拟（如“精选精读 / 全部论文”“按发布日期 / 按 Issue”）。
- 可取消的筛选（如主题标签）用按钮 toggle，再次点击取消。
- 折叠/展开按钮左侧放 chevron 图标，展开时旋转 180°。

## 验证与提交

- 前端构建：`pnpm --dir frontend build`（CI 同样会构建并检查 `out` 产物）。
- 类型检查：`pnpm --dir frontend typecheck`（tsc --noEmit，改动组件后跑一遍）。
- 纯前端修改（仅涉及 `frontend/` 内的组件、样式、类型或静态展示逻辑）在类型检查和生产构建通过后，默认直接提交并推送到 `main`，无需新建分支、PR 或再次询问是否推送；推送前确认当前分支为 `main`，且不混入无关改动。
- 如果改动同时涉及后端、数据管线、工作流或其他高风险范围，则遵循“小 PR”：基于最新 `main` 建分支，只提交本次改动；CI 通过后合并，GitHub Pages 由 `deploy-pages.yml` 自动部署，除非用户另有明确要求。

## 云端数据与密钥

本项目依赖远端 GitHub Actions 维护真实数据：

- `ANTHROPIC_API_KEY`、`SEMANTIC_SCHOLAR_API_KEY` 只存在于 GitHub Actions secrets。
- `SILICONFLOW_API_KEY` 只存在于 GitHub Actions secrets，用于 `tencent/Hunyuan-MT-7B` 翻译论文标题和摘要。
- `ANTHROPIC_BASE_URL`、`AI_MODEL` 只配置在 GitHub Actions variables。
- `backend/data/papers.db` 的有效版本保存在 Actions cache，本地仓库没有完整工作数据库。
- 不要向本地索取、补写或提交任何真实 API key，也不要提交 `.local/key.env` 或 `backend/data/papers.db`。

本地只运行不需要真实密钥的检查（类型检查、静态构建、JSON 校验、mock 单测）。凡是涉及真实抓取、LLM 筛选、方法回填、热点主题标注或完整数据更新，都必须：

1. 先提交并推送代码；
2. 手动触发对应的 `.github/workflows/*.yml`；
3. 监控 Actions 的步骤与日志；
4. 成功后同步 Actions 自动提交到 `main` 的公开数据。

不要把“本地缺少 key”当作需要用户补配置的问题；这是仓库的预期架构。

## 常用远端验证入口

- `.github/workflows/weekly-update.yml`：完整周更新、热点重建、静态构建、Pages 部署与公开数据回写。
- `.github/workflows/rebuild-hotspot-network.yml`：只从云端缓存数据库重建热点网络。
- `.github/workflows/backfill-journals.yml`：按年份回填期刊、筛选、方法标注、热点重建与部署。
- `.github/workflows/ci.yml`：普通代码与前端构建检查。
- `.github/workflows/translate-paper-library.yml`：从云端缓存数据库断点回填标题和摘要中文翻译；添加 `SILICONFLOW_API_KEY` 后再手动触发。

手动测试优先使用工作流已有的 `workflow_dispatch`，不要为了触发运行而提交无意义的 YAML 改动。若工作流没有 `workflow_dispatch`，先明确设计合适的触发方式，再修改工作流。

## 数据产物

- `frontend/public/data/papers.json`、`all_papers.json` 和 `hotspots/` 是可提交的静态站数据产物。
- `frontend/public/data/hotspots/` 由 GitHub Actions 重建，不应手工编辑。
- Actions 使用默认 `GITHUB_TOKEN` 产生的提交不会递归触发其他工作流；负责写数据的工作流应自行完成校验和部署。

## 当前研究方法标签

`method` 当前为单选：`质性分析 / 量化分析 / 理论分析 / 综述 / 计算传播学`，不确定时为空。新论文在 AI 筛选时写入，旧论文用 `label-methods` 回填。
