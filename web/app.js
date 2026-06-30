const state = {
  papers: [],
  featuredPapers: [],
  allPapers: [],
  mode: "featured",
  relevance: "all",
  tag: null,
  query: "",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function normalizeText(value) {
  if (Array.isArray(value)) {
    return value.join(" ");
  }
  return String(value ?? "");
}

function getAllTags(papers) {
  const counts = new Map();
  papers.forEach((paper) => {
    (paper.tags || []).forEach((tag) => {
      if (!tag) return;
      counts.set(tag, (counts.get(tag) || 0) + 1);
    });
  });

  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "zh-CN"))
    .map(([tag]) => tag);
}

function getDatasetPapers(viewState) {
  if (viewState.mode === "all") {
    return viewState.allPapers || [];
  }
  return viewState.featuredPapers || viewState.papers || [];
}

function filterPapers(papers, filters) {
  const query = filters.query.trim().toLowerCase();

  return papers
    .filter((paper) => {
      if (filters.relevance !== "all" && paper.relevance !== filters.relevance) {
        return false;
      }

      if (filters.tag) {
        const hasTag = (paper.tags || []).some(
          (tag) => tag.toLowerCase() === filters.tag.toLowerCase(),
        );
        if (!hasTag) return false;
      }

      if (!query) return true;

      const searchable = [
        paper.title,
        paper.summary,
        paper.reason,
        paper.journal,
        normalizeText(paper.authors),
        normalizeText(paper.tags),
      ].join(" ").toLowerCase();

      return searchable.includes(query);
    })
    .sort(comparePapers);
}

function comparePapers(a, b) {
  const aDate = Date.parse(a.published_date || "");
  const bDate = Date.parse(b.published_date || "");
  const aValid = Number.isFinite(aDate);
  const bValid = Number.isFinite(bDate);

  if (aValid && bValid && aDate !== bDate) {
    return bDate - aDate;
  }
  if (aValid !== bValid) {
    return aValid ? -1 : 1;
  }
  return Number(b.id || 0) - Number(a.id || 0);
}

function groupPapersByDate(papers) {
  return papers.reduce((groups, paper) => {
    const key = paper.published_date || "日期待补充";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(paper);
    return groups;
  }, new Map());
}

function createPaperCard(paper) {
  const relevance = paper.relevance || "Unrated";
  const badgeClass = relevance === "High" ? "high" : relevance === "Medium" ? "medium" : "";
  const scoreText = paper.score == null ? relevance : `${relevance} ${paper.score}`;
  const title = escapeHtml(paper.title || "Untitled paper");
  const titleContent = paper.source_url
    ? `<a class="paper-title" href="${escapeHtml(paper.source_url)}" target="_blank" rel="noopener">${title}</a>`
    : `<span class="paper-title">${title}</span>`;
  const authors = normalizeText(paper.authors);
  const meta = [authors, paper.journal].filter(Boolean).join(" · ");
  const tags = (paper.tags || [])
    .map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`)
    .join("");
  const summary = paper.summary
    ? `<p class="paper-summary">${escapeHtml(paper.summary)}</p>`
    : "";
  const reason = paper.reason
    ? `<div class="paper-reason">推荐理由：${escapeHtml(paper.reason)}</div>`
    : "";
  const doi = paper.doi
    ? `<a href="https://doi.org/${encodeURIComponent(paper.doi)}" target="_blank" rel="noopener">DOI</a>`
    : "";
  const source = paper.source_url
    ? `<a href="${escapeHtml(paper.source_url)}" target="_blank" rel="noopener">原文链接</a>`
    : "";
  const links = [doi, source].filter(Boolean).join("");

  return `
    <article class="paper-card">
      <div class="paper-topline">
        <span class="badge ${badgeClass}">${escapeHtml(scoreText)}</span>
        <span class="paper-date">${escapeHtml(paper.published_date || "日期待补充")}</span>
      </div>
      ${titleContent}
      ${meta ? `<div class="paper-meta">${escapeHtml(meta)}</div>` : ""}
      ${summary}
      ${reason}
      ${tags ? `<div class="paper-tags">${tags}</div>` : ""}
      ${links ? `<div class="paper-links">${links}</div>` : ""}
    </article>
  `;
}

function renderStats() {
  const papers = getDatasetPapers(state);
  const tags = getAllTags(papers);
  document.getElementById("stats").innerHTML = `
    <span>${papers.length} 篇</span>
    <span>${tags.length} 个主题</span>
  `;
}

function renderTags() {
  const tagCloud = document.getElementById("tagCloud");
  const clearButton = document.getElementById("clearTagButton");
  const tags = getAllTags(getDatasetPapers(state));

  if (tags.length === 0) {
    tagCloud.innerHTML = '<span class="feed-count">暂无标签</span>';
    clearButton.classList.add("hidden");
    return;
  }

  tagCloud.innerHTML = tags
    .map((tag) => {
      const active = state.tag && state.tag.toLowerCase() === tag.toLowerCase();
      return `<button class="tag ${active ? "active" : ""}" type="button" data-tag="${escapeHtml(tag)}">${escapeHtml(tag)}</button>`;
    })
    .join("");
  clearButton.classList.toggle("hidden", !state.tag);
}

function renderTimeline() {
  const timeline = document.getElementById("timeline");
  const emptyState = document.getElementById("emptyState");
  const feedCount = document.getElementById("feedCount");
  const papers = filterPapers(getDatasetPapers(state), state);

  feedCount.textContent = `${papers.length} 篇`;

  if (papers.length === 0) {
    timeline.innerHTML = "";
    emptyState.classList.remove("hidden");
    return;
  }

  emptyState.classList.add("hidden");
  const groups = groupPapersByDate(papers);
  timeline.innerHTML = Array.from(groups.entries())
    .map(([date, group]) => `
      <div class="day-group">
        <h3 class="day-heading">${escapeHtml(formatDateLabel(date))}</h3>
        ${group.map(createPaperCard).join("")}
      </div>
    `)
    .join("");
}

function formatDateLabel(value) {
  if (!value || value === "日期待补充") return "日期待补充";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short",
  });
}

function render() {
  renderStats();
  renderTags();
  renderTimeline();
}

async function loadPapers() {
  try {
    const [featuredResponse, allResponse] = await Promise.all([
      fetch("../public/data/papers.json", { cache: "no-store" }),
      fetch("../public/data/all_papers.json", { cache: "no-store" }),
    ]);
    if (!featuredResponse.ok) {
      throw new Error(`HTTP ${featuredResponse.status}`);
    }
    const featuredPayload = await featuredResponse.json();
    const allPayload = allResponse.ok ? await allResponse.json() : featuredPayload;
    state.featuredPapers = Array.isArray(featuredPayload) ? featuredPayload : [];
    state.allPapers = Array.isArray(allPayload) ? allPayload : state.featuredPapers;
    state.papers = state.featuredPapers;
    render();
  } catch (error) {
    document.getElementById("timeline").innerHTML = `
      <div class="empty-state">
        <strong>论文数据加载失败</strong>
        <span>请确认已运行 python -m src.main export-public，并从项目根目录启动静态服务器。</span>
      </div>
    `;
    document.getElementById("feedCount").textContent = "加载失败";
    console.error("Failed to load public papers:", error);
  }
}

function setTheme(theme) {
  const resolvedTheme = theme === "system" ? getSystemTheme() : theme;
  document.body.dataset.theme = resolvedTheme;
  document.body.dataset.themeMode = theme;
  localStorage.setItem("paper-hot-theme", theme);

  document.querySelectorAll(".theme-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.themeValue === theme);
  });
}

function getSystemTheme() {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function initTheme() {
  setTheme(localStorage.getItem("paper-hot-theme") || "system");
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (document.body.dataset.themeMode === "system") {
      setTheme("system");
    }
  });
}

function bindEvents() {
  document.querySelectorAll(".segment[data-relevance]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".segment[data-relevance]").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      state.relevance = button.dataset.relevance;
      renderTimeline();
    });
  });

  document.getElementById("searchInput").addEventListener("input", (event) => {
    state.query = event.target.value;
    renderTimeline();
  });

  document.querySelectorAll(".mode-segment").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".mode-segment").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      state.mode = button.dataset.mode;
      state.tag = null;
      render();
    });
  });

  document.getElementById("tagCloud").addEventListener("click", (event) => {
    const button = event.target.closest("[data-tag]");
    if (!button) return;
    state.tag = state.tag === button.dataset.tag ? null : button.dataset.tag;
    renderTags();
    renderTimeline();
  });

  document.getElementById("clearTagButton").addEventListener("click", () => {
    state.tag = null;
    renderTags();
    renderTimeline();
  });

  document.querySelectorAll(".theme-button").forEach((button) => {
    button.addEventListener("click", () => setTheme(button.dataset.themeValue));
  });
}

function init() {
  initTheme();
  bindEvents();
  loadPapers();
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", init);
}

if (typeof module !== "undefined") {
  module.exports = {
    comparePapers,
    createPaperCard,
    escapeHtml,
    filterPapers,
    getAllTags,
    getDatasetPapers,
    groupPapersByDate,
    normalizeText,
  };
}
