---
kind: frontend_style
name: Paper HOT 前端样式系统：Tailwind CSS v4 + Radix UI 组件库
category: frontend_style
scope:
    - '**'
source_files:
    - frontend/app/globals.css
    - frontend/app/sidebar.css
    - frontend/app/library.css
    - frontend/app/masonry.css
    - frontend/components/ui/button.tsx
    - frontend/components/ui/input.tsx
    - frontend/components/ui/select.tsx
    - frontend/components/ui/sheet.tsx
    - frontend/components/ui/tabs.tsx
    - frontend/components/ui/collapsible.tsx
    - frontend/postcss.config.mjs
    - frontend/package.json
---

## 样式系统与架构

Paper HOT 前端采用 **Tailwind CSS v4** 作为核心样式框架，结合 **Radix UI** 无样式基础组件和自研的 shadcn-style 组件封装，形成完整的视觉设计体系。

### 核心技术栈
- **Tailwind CSS v4.3.3**：通过 `@tailwindcss/postcss` 插件集成，使用新的 `@import "tailwindcss"` 语法
- **Radix UI**：提供无障碍基础组件（Dialog、Select、Tabs、Collapsible等）
- **class-variance-authority (CVA)**：用于组件变体管理
- **clsx + tailwind-merge**：条件类名合并工具
- **Lucide React**：图标库

### 设计令牌与主题系统
全局样式集中在 `app/globals.css`，通过 CSS 自定义属性实现主题系统：

```css
:root {
  --background: #fff;
  --foreground: #0a0a0a;
  --primary: #18181b;
  --secondary: #f4f4f5;
  /* ... 完整色彩系统 */
}
[data-theme="dark"] {
  --background: #09090b;
  --foreground: #fafafa;
  /* ... 暗色主题变量 */
}
```

支持通过 `data-theme="dark"` 属性切换明暗主题，使用 `@custom-variant dark (&:is([data-theme="dark"] *))` 定义暗色变体。

### 组件库架构
在 `components/ui/` 目录下构建了完整的 UI 组件库，每个组件遵循统一模式：

1. **Button** (`button.tsx`)：基于 CVA 定义变体（default、destructive、outline、secondary、ghost、link）和尺寸（sm、lg、icon）
2. **Input** (`input.tsx`)：统一的输入框样式，包含焦点状态和错误状态
3. **Select** (`select.tsx`)：完整的下拉选择器，包含滚动、分隔符等功能
4. **Sheet** (`sheet.tsx`)：侧边抽屉组件，支持多方向滑入
5. **Tabs** (`tabs.tsx`)：标签页组件
6. **Collapsible** (`collapsible.tsx`)：可折叠容器

所有组件都使用 `data-slot` 属性标记，便于样式定位和测试。

### 布局系统
- **Sidebar** (`sidebar.css`)：固定侧边栏，支持展开/收起状态，宽度从 224px 过渡到 64px
- **Main Content**：响应式主内容区，最大宽度 1440px，自动居中
- **Mobile Header**：移动端顶部导航栏

### 页面样式模块
- `library.css`：期刊图书馆样式，包含书架网格布局
- `masonry.css`：瀑布流布局，用于论文卡片展示
- `globals.css`：全局样式，包含论文卡片、热点网络、趋势表格等核心组件样式

### 响应式设计策略
采用移动优先的断点策略：
- `760px`：主要响应式断点，隐藏侧边栏，显示移动端头部
- `520px`：小屏幕优化，单列布局
- `680px`：瀑布流布局适配

### 字体与排版
- 英文字体：Georgia, serif
- 中文字体：Noto Sans SC, Microsoft YaHei, sans-serif
- 衬线字体：Noto Serif SC, Songti SC
- 行高：1.6（正文），1.2-1.4（标题）

### 构建配置
- PostCSS 配置仅包含 Tailwind 插件，保持简洁
- Next.js App Router 结构，样式文件按路由组织
- TypeScript 严格类型检查

该样式系统体现了现代 React 应用的最佳实践：原子化 CSS、组件化设计、无障碍支持和主题化能力。