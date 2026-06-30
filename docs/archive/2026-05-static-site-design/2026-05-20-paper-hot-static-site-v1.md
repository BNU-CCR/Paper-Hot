# Paper HOT 静态公开站第一版实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现一个纯静态论文情报站前端，读取 `public/data/papers.json` 并渲染 AI 筛选后的论文结果，支持主题切换、搜索、筛选和标签过滤。

**Architecture:** 纯静态 HTML/CSS/JS 前端，无后端，无构建工具。数据从现有 `public/data/papers.json` 加载。页面为单页，所有路由在页内完成。

**Tech Stack:** 原生 HTML5, CSS3 (CSS 变量), 原生 JavaScript (ES6+), 无框架, 无构建工具。

---

## 文件结构

新建文件：

| 文件 | 职责 |
|---|---|
| `web/index.html` | HTML 骨架：侧栏、主内容区、论文卡片模板、筛选面板 |
| `web/styles.css` | 全部样式：CSS 主题变量、侧栏布局、卡片、时间线、响应式、空状态 |
| `web/app.js` | 全部交互：fetch JSON、主题切换、筛选、搜索、标签过滤、渲染 |

使用已有文件（只读）：

| 文件 | 职责 |
|---|---|
| `public/data/papers.json` | 数据源，由 `python -m src.main export-public` 生成 |

---

### Task 1: 创建 HTML 骨架

**Files:**
- Create: `web/index.html`

- [ ] **Step 1: 编写 HTML 骨架**

包含：
- `head`：meta charset utf-8, viewport, title "Paper HOT", link styles.css
- `body`：
  - `<aside class="sidebar">`：
    - `<div class="logo">Paper HOT</div>`
    - `<nav>`：精选论文、主题标签、关于（页内锚点）
    - `<div class="theme-toggle">`：三段式按钮（light/system/dark），初始状态跟随系统
  - `<main class="main">`：
    - `<header class="page-header">`：
      - `<h1>` 精选论文
      - `<p class="subtitle">` AI 辅助整理的计算传播论文精选
      - `<div class="filters">`：全部、High、Medium 按钮
      - `<input class="search" type="text" placeholder="搜索标题、摘要、作者...">`
    - `<div class="tags-section">`：
      - `<div class="tags-list">` 由 JS 动态填充
      - `<button class="clear-tags hidden">` 清除筛选
    - `<div class="timeline" id="timeline">` 由 JS 动态填充
    - `<div class="empty-state hidden" id="empty">` 没有匹配论文

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Paper HOT - 计算传播论文精选</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body data-theme="system">
  <aside class="sidebar">
    <div class="logo">
      <span class="logo-brand">Paper</span>
      <span class="logo-dot"></span>
      <span class="logo-brand">HOT</span>
    </div>
    <nav class="nav">
      <a href="#" class="nav-item active" data-view="featured">精选论文</a>
      <a href="#tags" class="nav-item" data-view="tags">主题标签</a>
      <a href="#about" class="nav-item" data-view="about">关于</a>
    </nav>
    <div class="theme-toggle">
      <button class="theme-btn" data-theme="light" title="浅色">🌙</button>
      <button class="theme-btn active" data-theme="system" title="跟随系统">💻</button>
      <button class="theme-btn" data-theme="dark" title="深色">☀️</button>
    </div>
  </aside>

  <main class="main">
    <header class="page-header">
      <h1>精选论文</h1>
      <p class="subtitle">AI 辅助整理的计算传播论文精选</p>
      <div class="filters">
        <button class="filter-btn active" data-relevance="all">全部</button>
        <button class="filter-btn" data-relevance="High">High</button>
        <button class="filter-btn" data-relevance="Medium">Medium</button>
      </div>
      <input type="text" class="search" placeholder="搜索标题、摘要、作者、期刊、标签...">
    </header>

    <div class="tags-section">
      <div class="tags-list" id="tags"></div>
      <button class="clear-tags hidden" id="clearTags">清除筛选</button>
    </div>

    <div class="timeline" id="timeline"></div>

    <div class="empty-state hidden" id="empty">
      <p>没有匹配当前筛选条件的论文。</p>
    </div>
  </main>

  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add web/index.html
git commit -m "feat(web): add HTML skeleton for Paper HOT static site"
```

---

### Task 2: 创建 CSS 主题与布局样式

**Files:**
- Create: `web/styles.css`

- [ ] **Step 1: 编写 CSS 根变量与主题系统**

定义 `:root` 下的 CSS 自定义属性，包含两套变量映射：

```css
/* ===== CSS Variables ===== */
:root {
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif;
  --font-mono: "SF Mono", "Cascadia Code", "Fira Code", monospace;

  /* Light theme (default) */
  --bg: #f7f9fc;
  --surface: #ffffff;
  --surface-hover: #f0f4f8;
  --border: #e2e8f0;
  --border-light: #f1f5f9;
  --text-primary: #1e293b;
  --text-secondary: #64748b;
  --text-tertiary: #94a3b8;
  --accent: #06b6d4;
  --accent-hover: #0891b2;
  --high: #10b981;
  --high-bg: #d1fae5;
  --medium: #f59e0b;
  --medium-bg: #fef3c7;
  --reason-bg: #ecfdf5;
  --reason-text: #065f46;
  --sidebar-bg: #ffffff;
  --sidebar-border: #e2e8f0;
  --tag-bg: #f1f5f9;
  --tag-active-bg: #06b6d4;
  --tag-active-text: #ffffff;
  --timeline-line: #e2e8f0;
  --timeline-dot: #06b6d4;
  --shadow: 0 1px 3px rgba(0,0,0,0.05);
  --shadow-hover: 0 4px 12px rgba(0,0,0,0.08);
}

/* Dark theme overrides */
[data-theme="dark"] {
  --bg: #060814;
  --surface: rgba(255,255,255,0.04);
  --surface-hover: rgba(255,255,255,0.08);
  --border: rgba(255,255,255,0.08);
  --border-light: rgba(255,255,255,0.04);
  --text-primary: #e2e8f0;
  --text-secondary: #94a3b8;
  --text-tertiary: #64748b;
  --accent: #22d3ee;
  --accent-hover: #67e8f9;
  --high: #34d399;
  --high-bg: rgba(52,211,153,0.15);
  --medium: #fbbf24;
  --medium-bg: rgba(251,191,36,0.15);
  --reason-bg: rgba(52,211,153,0.08);
  --reason-text: #6ee7b7;
  --sidebar-bg: #0b1020;
  --sidebar-border: rgba(255,255,255,0.06);
  --tag-bg: rgba(255,255,255,0.06);
  --tag-active-bg: #22d3ee;
  --tag-active-text: #060814;
  --timeline-line: rgba(255,255,255,0.08);
  --timeline-dot: #22d3ee;
  --shadow: 0 1px 3px rgba(0,0,0,0.3);
  --shadow-hover: 0 4px 12px rgba(0,0,0,0.4);
}
```

- [ ] **Step 2: 编写全局样式、重置与布局**

```css
/* ===== Reset & Base ===== */
* { box-sizing: border-box; margin: 0; padding: 0; }

html {
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  font-family: var(--font-sans);
  background: var(--bg);
  color: var(--text-primary);
  line-height: 1.6;
  min-height: 100vh;
  display: flex;
}

a {
  color: var(--accent);
  text-decoration: none;
}
a:hover { color: var(--accent-hover); }

.hidden { display: none !important; }
```

- [ ] **Step 3: 编写侧栏样式**

```css
/* ===== Sidebar ===== */
.sidebar {
  width: 200px;
  flex-shrink: 0;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--sidebar-border);
  display: flex;
  flex-direction: column;
  padding: 24px 16px;
  position: fixed;
  top: 0; left: 0; bottom: 0;
  z-index: 100;
}

.logo {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 32px;
}
.logo-brand { letter-spacing: -0.02em; }
.logo-dot {
  width: 6px; height: 6px;
  background: var(--accent);
  border-radius: 50%;
}

.nav { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.nav-item {
  padding: 8px 12px;
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 0.9375rem;
  transition: all 0.15s;
}
.nav-item:hover { background: var(--surface-hover); color: var(--text-primary); }
.nav-item.active { background: var(--surface-hover); color: var(--accent); font-weight: 500; }

.theme-toggle {
  display: flex;
  gap: 4px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}
.theme-btn {
  flex: 1;
  padding: 6px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.15s;
}
.theme-btn:hover { background: var(--surface-hover); }
.theme-btn.active {
  background: var(--accent);
  color: var(--sidebar-bg);
  border-color: var(--accent);
}
```

- [ ] **Step 4: 编写主内容区与头部样式**

```css
/* ===== Main Content ===== */
.main {
  flex: 1;
  margin-left: 200px;
  padding: 32px 40px;
  max-width: 900px;
}

.page-header { margin-bottom: 32px; }
.page-header h1 {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 4px;
}
.subtitle {
  color: var(--text-secondary);
  font-size: 0.9375rem;
  margin-bottom: 20px;
}

.filters {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.filter-btn {
  padding: 6px 16px;
  border: 1px solid var(--border);
  border-radius: 20px;
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.15s;
}
.filter-btn:hover { border-color: var(--accent); color: var(--accent); }
.filter-btn.active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

.search {
  width: 100%;
  max-width: 400px;
  padding: 10px 16px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text-primary);
  font-size: 0.9375rem;
  outline: none;
  transition: border-color 0.15s;
}
.search:focus { border-color: var(--accent); }
.search::placeholder { color: var(--text-tertiary); }
```

- [ ] **Step 5: 编写标签与论文卡片样式**

```css
/* ===== Tags ===== */
.tags-section { margin-bottom: 24px; }
.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tag {
  padding: 4px 12px;
  border-radius: 16px;
  background: var(--tag-bg);
  color: var(--text-secondary);
  font-size: 0.8125rem;
  cursor: pointer;
  transition: all 0.15s;
  border: none;
}
.tag:hover { background: var(--surface-hover); color: var(--text-primary); }
.tag.active {
  background: var(--tag-active-bg);
  color: var(--tag-active-text);
}
.clear-tags {
  margin-top: 8px;
  padding: 4px 12px;
  border: none;
  background: transparent;
  color: var(--accent);
  font-size: 0.8125rem;
  cursor: pointer;
}

/* ===== Timeline & Paper Card ===== */
.timeline {
  position: relative;
  padding-left: 24px;
}
.timeline::before {
  content: '';
  position: absolute;
  left: 7px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--timeline-line);
}

.paper-card {
  position: relative;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 20px;
  box-shadow: var(--shadow);
  transition: box-shadow 0.15s, transform 0.15s;
}
.paper-card:hover { box-shadow: var(--shadow-hover); transform: translateY(-1px); }

.paper-card::before {
  content: '';
  position: absolute;
  left: -20px;
  top: 28px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--timeline-dot);
  border: 2px solid var(--bg);
}

.badge-row { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  font-family: var(--font-mono);
}
.badge.high { background: var(--high-bg); color: var(--high); }
.badge.medium { background: var(--medium-bg); color: var(--medium); }

.paper-title {
  font-size: 1.125rem;
  font-weight: 600;
  line-height: 1.4;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.paper-meta {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.paper-summary {
  font-size: 0.9375rem;
  color: var(--text-primary);
  line-height: 1.7;
  margin-bottom: 12px;
}

.paper-reason {
  background: var(--reason-bg);
  border-left: 3px solid var(--high);
  padding: 10px 14px;
  border-radius: 0 8px 8px 0;
  font-size: 0.875rem;
  color: var(--reason-text);
  margin-bottom: 12px;
}

.paper-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}
.paper-tags .tag { cursor: default; }

.paper-links { display: flex; gap: 16px; }
.paper-links a {
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 4px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-tertiary);
}
```

- [ ] **Step 6: 编写响应式样式**

```css
/* ===== Responsive ===== */
@media (max-width: 768px) {
  .sidebar {
    width: 100%;
    position: static;
    flex-direction: row;
    align-items: center;
    padding: 12px 16px;
    border-right: none;
    border-bottom: 1px solid var(--sidebar-border);
  }
  .logo { margin-bottom: 0; margin-right: auto; }
  .nav { flex-direction: row; gap: 8px; margin: 0 16px; }
  .theme-toggle { padding-top: 0; border-top: none; }
  .main { margin-left: 0; padding: 20px 16px; max-width: none; }
  .timeline { padding-left: 0; }
  .timeline::before { display: none; }
  .paper-card::before { display: none; }
}

@media (max-width: 480px) {
  .filters { flex-wrap: wrap; }
  .page-header h1 { font-size: 1.25rem; }
}
```

- [ ] **Step 7: Commit**

```bash
git add web/styles.css
git commit -m "feat(web): add CSS with dual themes, timeline layout, paper cards"
```

---

### Task 3: 创建 app.js 交互逻辑

**Files:**
- Create: `web/app.js`

- [ ] **Step 1: 编写数据加载与状态管理**

```javascript
// ===== State =====
let allPapers = [];
let currentFilter = { relevance: 'all', tag: null, query: '' };

// ===== Data Loading =====
async function loadPapers() {
  try {
    const res = await fetch('../public/data/papers.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    allPapers = await res.json();
    renderTags();
    applyFilters();
  } catch (err) {
    console.error('Failed to load papers:', err);
    document.getElementById('timeline').innerHTML =
      '<div class="empty-state">加载论文数据失败，请确保已运行 <code>python -m src.main export-public</code></div>';
    document.getElementById('empty').classList.add('hidden');
  }
}
```

- [ ] **Step 2: 编写筛选与搜索逻辑**

```javascript
// ===== Filtering =====
function getFilteredPapers() {
  let result = [...allPapers];

  // Relevance filter
  if (currentFilter.relevance !== 'all') {
    result = result.filter(p => p.relevance === currentFilter.relevance);
  }

  // Tag filter
  if (currentFilter.tag) {
    result = result.filter(p =>
      (p.tags || []).some(t => t.toLowerCase() === currentFilter.tag.toLowerCase())
    );
  }

  // Search filter
  if (currentFilter.query) {
    const q = currentFilter.query.toLowerCase();
    result = result.filter(p => {
      const fields = [
        p.title, p.summary, p.reason,
        Array.isArray(p.authors) ? p.authors.join(' ') : p.authors,
        p.journal,
        Array.isArray(p.tags) ? p.tags.join(' ') : p.tags
      ];
      return fields.some(f => f && f.toLowerCase().includes(q));
    });
  }

  // Sort by published_date descending, fallback to id descending
  result.sort((a, b) => {
    if (a.published_date && b.published_date) {
      return new Date(b.published_date) - new Date(a.published_date);
    }
    return (b.id || 0) - (a.id || 0);
  });

  return result;
}
```

- [ ] **Step 3: 编写标签渲染与标签聚合**

```javascript
// ===== Tags =====
function getAllTags() {
  const tagCounts = new Map();
  allPapers.forEach(p => {
    (p.tags || []).forEach(tag => {
      tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1);
    });
  });
  return Array.from(tagCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([tag]) => tag);
}

function renderTags() {
  const container = document.getElementById('tags');
  const tags = getAllTags();
  if (tags.length === 0) {
    container.innerHTML = '';
    return;
  }
  container.innerHTML = tags.map(tag => {
    const isActive = currentFilter.tag && currentFilter.tag.toLowerCase() === tag.toLowerCase();
    return `<button class="tag ${isActive ? 'active' : ''}" data-tag="${escapeHtml(tag)}">${escapeHtml(tag)}</button>`;
  }).join('');

  // Toggle clear button
  document.getElementById('clearTags').classList.toggle('hidden', !currentFilter.tag);
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
```

- [ ] **Step 4: 编写论文卡片渲染**

```javascript
// ===== Paper Card Rendering =====
function renderPapers() {
  const container = document.getElementById('timeline');
  const empty = document.getElementById('empty');
  const papers = getFilteredPapers();

  if (papers.length === 0) {
    container.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }

  empty.classList.add('hidden');
  container.innerHTML = papers.map(p => createPaperCard(p)).join('');
}

function createPaperCard(p) {
  const badgeClass = p.relevance === 'High' ? 'high' : (p.relevance === 'Medium' ? 'medium' : '');
  const scoreHtml = p.score != null ? `<span class="badge ${badgeClass}">${p.relevance} ${p.score}</span>`
    : `<span class="badge ${badgeClass}">${p.relevance}</span>`;
  const authorsHtml = Array.isArray(p.authors) ? p.authors.join(', ') : p.authors;
  const metaHtml = [authorsHtml, p.journal, p.published_date]
    .filter(Boolean)
    .join(' · ');
  const summaryHtml = p.summary ? `<div class="paper-summary">${escapeHtml(p.summary)}</div>` : '';
  const reasonHtml = p.reason ? `<div class="paper-reason">${escapeHtml(p.reason)}</div>` : '';
  const tagsHtml = (p.tags || []).map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('');
  const doiHtml = p.doi ? `<a href="https://doi.org/${encodeURIComponent(p.doi)}" target="_blank" rel="noopener">📄 DOI</a>` : '';
  const sourceHtml = p.source_url ? `<a href="${escapeHtml(p.source_url)}" target="_blank" rel="noopener">🔗 原文</a>` : '';
  const linksHtml = [doiHtml, sourceHtml].filter(Boolean).join('');

  return `
    <article class="paper-card">
      <div class="badge-row">${scoreHtml}</div>
      <h3 class="paper-title">${escapeHtml(p.title)}</h3>
      <div class="paper-meta">${escapeHtml(metaHtml)}</div>
      ${summaryHtml}
      ${reasonHtml}
      <div class="paper-tags">${tagsHtml}</div>
      <div class="paper-links">${linksHtml}</div>
    </article>
  `;
}
```

- [ ] **Step 5: 编写事件绑定**

```javascript
// ===== Event Bindings =====
function bindEvents() {
  // Relevance filters
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter.relevance = btn.dataset.relevance;
      applyFilters();
    });
  });

  // Search
  const searchInput = document.querySelector('.search');
  searchInput.addEventListener('input', (e) => {
    currentFilter.query = e.target.value.trim();
    applyFilters();
  });

  // Tag clicks (delegation)
  document.getElementById('tags').addEventListener('click', (e) => {
    const tagBtn = e.target.closest('.tag');
    if (!tagBtn) return;
    const tag = tagBtn.dataset.tag;
    if (currentFilter.tag === tag) {
      currentFilter.tag = null;
    } else {
      currentFilter.tag = tag;
    }
    renderTags();
    applyFilters();
  });

  // Clear tags
  document.getElementById('clearTags').addEventListener('click', () => {
    currentFilter.tag = null;
    renderTags();
    applyFilters();
  });

  // Theme toggle
  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const theme = btn.dataset.theme;
      setTheme(theme);
    });
  });
}

function applyFilters() {
  renderPapers();
}
```

- [ ] **Step 6: 编写主题切换逻辑**

```javascript
// ===== Theme =====
function setTheme(theme) {
  document.body.dataset.theme = theme;
  localStorage.setItem('paperhot-theme', theme);

  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.theme === theme);
  });
}

function initTheme() {
  const saved = localStorage.getItem('paperhot-theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

  if (saved) {
    setTheme(saved);
  } else if (prefersDark) {
    setTheme('dark');
  } else {
    setTheme('light');
  }

  // Listen for system changes when in system mode
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (document.body.dataset.theme === 'system') {
      document.body.classList.toggle('dark', e.matches);
    }
  });
}
```

- [ ] **Step 7: 编写初始化入口**

```javascript
// ===== Init =====
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  bindEvents();
  loadPapers();
});
```

- [ ] **Step 8: Commit**

```bash
git add web/app.js
git commit -m "feat(web): add JS with filtering, search, tags, theme toggle"
```

---

### Task 4: 本地验证

**Files:**
- Read: `web/index.html`, `web/styles.css`, `web/app.js`
- Read: `public/data/papers.json`

- [ ] **Step 1: 确认公开数据已导出**

```bash
python -m src.main export-public
```

预期输出包含 `已导出公开数据到:` 和路径。检查 `public/data/papers.json` 非空。

- [ ] **Step 2: 启动本地服务器**

从项目根目录启动，使 `web/app.js` 可以通过 `../public/data/papers.json` 访问数据：

```bash
cd "e:/OneDrive/Claude Code/期刊追踪"
python -m http.server 8000
```

然后在浏览器打开 `http://localhost:8000/web/`

- [ ] **Step 3: 手动验证清单**

逐项检查：

- [ ] 页面能正常加载，不报错。
- [ ] 能看到论文卡片（至少当前测试论文）。
- [ ] 论文卡片显示标题、作者、期刊、relevance badge。
- [ ] 如果测试论文有 summary/reason/tags，这些字段正确显示。
- [ ] 点击 `High` 筛选按钮，只显示 High 论文。
- [ ] 点击 `Medium` 筛选按钮，只显示 Medium 论文。
- [ ] 点击 `全部` 恢复显示所有论文。
- [ ] 标签列表从论文 tags 自动聚合。
- [ ] 点击某个标签后只显示包含该标签的论文。
- [ ] 点击 "清除筛选" 恢复显示所有标签。
- [ ] 搜索框输入关键词后实时过滤。
- [ ] 搜索无结果时显示空状态提示。
- [ ] 点击 light/system/dark 主题切换，页面颜色和对比度变化。
- [ ] 刷新页面后主题偏好被保留（通过 localStorage）。
- [ ] 移动端（浏览器 DevTools 设备模拟）侧栏变为顶部横向布局。
- [ ] 页面不暴露 API Key、Prompt、配置文件或 Low 论文（检查 Network 面板只请求 papers.json）。

- [ ] **Step 4: Commit 验证结果**

验证通过后：

```bash
git add web/
git commit -m "feat(web): complete Paper HOT static site v1"
```

---

## Self-Review

### Spec coverage check

| Spec 要求 | 对应任务/步骤 |
|---|---|
| 纯静态站，读取 `public/data/papers.json` | Task 3 Step 1 `loadPapers()` |
| 侧栏 + 主内容区 | Task 1 HTML, Task 2 CSS |
| light/dark/system 三段主题 | Task 3 Step 6 `initTheme`/`setTheme`, Task 2 CSS 变量 |
| High/Medium/全部 筛选 | Task 3 Step 2 `getFilteredPapers`, Step 5 事件绑定 |
| 标签筛选 | Task 3 Step 2, 3, 5 |
| 搜索标题/摘要/作者/期刊/标签 | Task 3 Step 2 `getFilteredPapers` |
| 时间线式论文流 | Task 2 CSS `.timeline::before`, `.paper-card::before` |
| 展示 AI 摘要、推荐理由、标签、分数、原文链接 | Task 3 Step 4 `createPaperCard` |
| 空字段不显示破碎 UI | Task 3 Step 4 使用条件渲染 `|| ''` |
| 不暴露配置/Prompt/API Key/Low 论文 | 前端只 fetch JSON，不读其他文件 |

### Placeholder scan

- 无 "TBD"/"TODO" 占位符。
- 无 "add appropriate error handling" 模糊描述。
- 所有代码步骤包含完整代码。
- 验证步骤包含具体检查清单。

### Type consistency

- 字段名与 `publication.py` 导出字段一致：`title`, `authors`, `journal`, `published_date`, `relevance`, `score`, `summary`, `reason`, `tags`, `doi`, `source_url`。
- `authors` 和 `tags` 假设为数组（与 exporter 输出一致）。
- `score` 可能为 null，使用 `p.score != null` 检查。