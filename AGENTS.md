# Paper HOT 设计规范（Codex + Claude 共用）

Codex 与 Claude Code 都会自动读取仓库根目录的 `AGENTS.md`。改动前端 UI 前必读；后端/数据相关约定见 `CLAUDE.md`。

## 设计体系

- 组件库为 shadcn/ui 风格：Radix primitives + CSS 变量，包装组件在 `frontend/components/ui/`，类名用 `cn()` 合并。
- 图标统一用 `lucide-react`，尺寸 14–16px；装饰性图标加 `aria-hidden="true"`。
- 标题用衬线（Georgia / "Noto Serif SC" / "Songti SC"），正文用系统无衬线；颜色、圆角、间距沿用现有 CSS 变量（`--radius`、`--border`、`--muted-foreground` 等），不写死值。
- 亮/暗主题通过 `data-theme` + CSS 变量切换，不要硬编码颜色。
- 布局：左侧固定 `sidebar`（224px）+ `main` 内容区；页面级 hero 用 `.eyebrow` + `h1`；工具条放 `.toolbar` / `.library-toolbar`（`shadcn-controls`）。

## 标题与标签：一个区块只保留一个标题

- 每个 section 只保留一个语义标题（h2/h3）。禁止 `.eyebrow` 小标签与标题成对表达同一语义（例如“按主题浏览 / 主题标签”“期刊论文 / 论文列表”这种重复写法）。
- `.eyebrow` 只允许出现在页面级 hero（`h1` 上方）作为补充语境，或作为独立小标注（如 Issue 侧栏），不得与相邻标题语义重复。
- 数量、日期等元信息放标题右侧的 `.count` 等辅助元素，不要另起小标题。

## 不要占位提示

- 不要在页面或功能底部放置常驻的解释性提示文本（例如“点击标签筛选论文，再次点击可取消”）。需要说明时用真实状态或空状态表达，而不是 hint 段落。
- 状态反馈只在状态真实存在时渲染（如筛选生效时显示“当前筛选 …”状态条）。
- 空状态（`.empty-state`）只在确实无数据时出现，文案给出可执行动作。

## 交互控件

- 二选一/多选一切换用 Tabs（`TabsList`/`TabsTrigger`），不要用普通 Button 模拟（如“精选精读 / 全部论文”“按发布日期 / 按 Issue”）。
- 可取消的筛选（如主题标签）用按钮 toggle，再次点击取消。
- 折叠/展开按钮左侧放 chevron 图标，展开时旋转 180°。

## 验证与提交

- 前端构建：`pnpm --dir frontend build`（CI 同样会构建并检查 `out` 产物）。
- 提交遵循“小 PR”：基于最新 `main` 建分支，只提交本次改动；CI 通过后合并，GitHub Pages 由 `deploy-pages.yml` 自动部署。
