"use client";

import { useEffect, useMemo, useState } from "react";

const GITHUB_URL = "https://github.com/BNU-CCR/Paper-Hot";

function asText(value) {
  return Array.isArray(value) ? value.join(" ") : String(value || "");
}

function sortPapers(papers) {
  return [...papers].sort((a, b) => {
    const aDate = Date.parse(a.published_date || "");
    const bDate = Date.parse(b.published_date || "");
    if (Number.isFinite(aDate) && Number.isFinite(bDate) && aDate !== bDate) return bDate - aDate;
    if (Number.isFinite(aDate) !== Number.isFinite(bDate)) return Number.isFinite(aDate) ? -1 : 1;
    return Number(b.id || 0) - Number(a.id || 0);
  });
}

function displayDate(value) {
  if (!value) return "日期待补充";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric", weekday: "short" });
}

function PaperCard({ paper }) {
  const relevance = paper.relevance || "Unrated";
  const score = paper.score == null ? relevance : `${relevance} ${paper.score}`;
  return (
    <article className="paper-card">
      <div className="paper-topline">
        <span className={`badge ${relevance.toLowerCase()}`}>{score}</span>
        <time>{paper.published_date || "日期待补充"}</time>
      </div>
      {paper.source_url ? (
        <a className="paper-title" href={paper.source_url} target="_blank" rel="noreferrer">{paper.title || "Untitled paper"}</a>
      ) : <h3 className="paper-title">{paper.title || "Untitled paper"}</h3>}
      {(paper.authors || paper.journal) && <p className="paper-meta">{[asText(paper.authors), paper.journal].filter(Boolean).join(" · ")}</p>}
      {paper.summary && <p className="paper-summary">{paper.summary}</p>}
      {paper.reason && <p className="paper-reason"><b>推荐理由</b>{paper.reason}</p>}
      <div className="paper-tags">
        {(paper.tags || []).map((tag) => <span key={tag} className="tag">{tag}</span>)}
      </div>
      <div className="paper-links">
        {paper.doi && <a href={`https://doi.org/${encodeURIComponent(paper.doi)}`} target="_blank" rel="noreferrer">DOI</a>}
        {paper.source_url && <a href={paper.source_url} target="_blank" rel="noreferrer">原文</a>}
      </div>
    </article>
  );
}

export default function HomePage() {
  const [featured, setFeatured] = useState([]);
  const [allPapers, setAllPapers] = useState([]);
  const [mode, setMode] = useState("featured");
  const [relevance, setRelevance] = useState("all");
  const [journal, setJournal] = useState("all");
  const [tag, setTag] = useState(null);
  const [query, setQuery] = useState("");
  const [tagsOpen, setTagsOpen] = useState(false);
  const [theme, setTheme] = useState("system");
  const [loadingError, setLoadingError] = useState("");

  useEffect(() => {
    const stored = window.localStorage.getItem("paper-hot-theme") || "system";
    setTheme(stored);
  }, []);

  useEffect(() => {
    const resolved = theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : theme === "system" ? "light" : theme;
    document.documentElement.dataset.theme = resolved;
    window.localStorage.setItem("paper-hot-theme", theme);
  }, [theme]);

  useEffect(() => {
    Promise.all([fetch("data/papers.json", { cache: "no-store" }), fetch("data/all_papers.json", { cache: "no-store" })])
      .then(async ([featuredResponse, allResponse]) => {
        if (!featuredResponse.ok) throw new Error(`精选数据 HTTP ${featuredResponse.status}`);
        const featuredData = await featuredResponse.json();
        const allData = allResponse.ok ? await allResponse.json() : featuredData;
        setFeatured(Array.isArray(featuredData) ? featuredData : []);
        setAllPapers(Array.isArray(allData) ? allData : featuredData);
      })
      .catch((error) => setLoadingError(error.message));
  }, []);

  const source = mode === "all" ? allPapers : featured;
  const journals = useMemo(() => [...new Set(source.map((paper) => paper.journal).filter(Boolean))].sort((a, b) => a.localeCompare(b, "zh-CN")), [source]);
  const tags = useMemo(() => {
    const count = new Map();
    source.forEach((paper) => (paper.tags || []).forEach((item) => count.set(item, (count.get(item) || 0) + 1)));
    return [...count.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "zh-CN"));
  }, [source]);
  const papers = useMemo(() => sortPapers(source.filter((paper) => {
    if (relevance !== "all" && paper.relevance !== relevance) return false;
    if (journal !== "all" && paper.journal !== journal) return false;
    if (tag && !(paper.tags || []).some((item) => item.toLowerCase() === tag.toLowerCase())) return false;
    const needle = query.trim().toLowerCase();
    return !needle || [paper.title, paper.summary, paper.reason, paper.journal, asText(paper.authors), asText(paper.tags)].join(" ").toLowerCase().includes(needle);
  })), [source, relevance, journal, tag, query]);

  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="brand" href="./"><span>Paper</span><i /><span>HOT</span></a>
        <nav aria-label="主导航"><a className="active" href="./">精选论文</a><a href="journals/">期刊书库</a><a href="about/">关于项目</a></nav>
        <a className="github-link" href={GITHUB_URL} target="_blank" rel="noreferrer">GitHub ↗</a>
        <div className="theme-switch" aria-label="主题切换">
          {[['dark', '☾'], ['system', '◐'], ['light', '☼']].map(([value, icon]) => <button key={value} className={theme === value ? "active" : ""} onClick={() => setTheme(value)} aria-label={`${value} theme`}>{icon}</button>)}
        </div>
      </aside>
      <main className="main">
        <section className="hero">
          <div className="eyebrow">AI 辅助整理 · 计算传播论文精选</div>
          <div className="headline"><div><h1>Paper HOT</h1><p>追踪计算传播研究的新论文，保留可复核的摘要、主题和推荐理由。</p></div><div className="stats"><span>{source.length} 篇公开</span><span>{tags.length} 个主题</span></div></div>
          <div className="toolbar">
            <div className="segmented" aria-label="数据范围"><button className={mode === "featured" ? "active" : ""} onClick={() => setMode("featured")}>精选</button><button className={mode === "all" ? "active" : ""} onClick={() => setMode("all")}>期刊全量</button></div>
            <div className="segmented" aria-label="相关性筛选">{["all", "High", "Medium"].map((item) => <button key={item} className={relevance === item ? "active" : ""} onClick={() => setRelevance(item)}>{item === "all" ? "全部" : item}</button>)}</div>
            <label className="select-label">期刊<select value={journal} onChange={(event) => setJournal(event.target.value)}><option value="all">全部期刊</option>{journals.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
            <label className="search"><span className="sr-only">搜索论文</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索标题、摘要、作者、期刊、标签" /></label>
          </div>
        </section>

        <section className="topics-panel">
          <div className="section-heading"><div><p className="eyebrow">按主题浏览</p><h2>主题标签</h2></div><div className="section-actions"><button className="text-button" onClick={() => setTagsOpen((value) => !value)} aria-expanded={tagsOpen}>{tagsOpen ? "收起标签" : `展开全部 ${tags.length} 个标签`}</button>{tag && <button className="text-button" onClick={() => setTag(null)}>清除筛选</button>}</div></div>
          <div className={`tag-cloud ${tagsOpen ? "open" : ""}`}>{tags.map(([item, count], index) => <button key={item} className={`tag ${tag === item ? "active" : ""} ${index > 11 ? "overflow-tag" : ""}`} onClick={() => setTag(tag === item ? null : item)}>{item}<small>{count}</small></button>)}</div>
        </section>

        <section className="feed"><div className="section-heading"><div><p className="eyebrow">最新更新</p><h2>{mode === "featured" ? "最新精选" : "期刊全量更新"}</h2></div><span className="count">{papers.length} 篇</span></div>
          {loadingError ? <div className="empty-state"><b>论文数据加载失败</b><span>{loadingError}</span></div> : papers.length === 0 ? <div className="empty-state"><b>没有匹配当前条件的论文</b><span>可以调整期刊、主题、相关性或搜索词。</span></div> : <div className="timeline">{Object.entries(papers.reduce((groups, paper) => { const key = paper.published_date || "日期待补充"; (groups[key] ||= []).push(paper); return groups; }, {})).map(([date, group]) => <section className="day-group" key={date}><h3>{displayDate(date)}</h3>{group.map((paper) => <PaperCard key={paper.id || `${paper.title}-${paper.published_date}`} paper={paper} />)}</section>)}</div>}
        </section>
      </main>
    </div>
  );
}
