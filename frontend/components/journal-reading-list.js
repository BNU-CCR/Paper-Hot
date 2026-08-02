"use client";

import Link from "next/link";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { AppSidebar } from "./app-sidebar";
import { Tabs, TabsList, TabsTrigger } from "./ui/tabs";

function asText(value) { return Array.isArray(value) ? value.join(" ") : String(value || ""); }
function sortPapers(papers) { return [...papers].sort((a, b) => Date.parse(b.published_date || 0) - Date.parse(a.published_date || 0)); }
function matchesJournal(paper, journal) {
  const aliases = new Set([journal.name, journal.name.replace(", ", " "), journal.name.replace("Revista Icono 14", "Revista ICONO14"), "Information Communication & Society"]);
  return aliases.has(paper.journal);
}

function issueGroups(papers) {
  const groups = new Map();
  papers.forEach((paper) => {
    const volume = String(paper.volume || "").trim();
    const issue = String(paper.issue || "").trim();
    const key = issue ? `${volume || "no-volume"}-${issue}` : "unassigned";
    if (!groups.has(key)) groups.set(key, { key, volume, issue, papers: [] });
    groups.get(key).papers.push(paper);
  });
  return [...groups.values()].sort((a, b) => {
    if (!a.issue) return 1;
    if (!b.issue) return -1;
    return `${b.volume}-${b.issue}`.localeCompare(`${a.volume}-${a.issue}`, "en", { numeric: true });
  });
}

function issueLabel(group) {
  if (!group.issue) return "未分期";
  return group.volume ? `Vol. ${group.volume} · Issue ${group.issue}` : `Issue ${group.issue}`;
}

function JournalPaperCard({ paper }) {
  return <article className="paper-card" key={paper.id || paper.title}>
    <div className="paper-topline"><span className={`badge ${(paper.relevance || "").toLowerCase()}`}>{paper.score == null ? paper.relevance : `${paper.relevance} ${paper.score}`}</span><time>{paper.published_date || "日期待补充"}</time></div>
    {paper.source_url ? <a className="paper-title" href={paper.source_url} target="_blank" rel="noreferrer">{paper.title}</a> : <h3 className="paper-title">{paper.title}</h3>}
    {paper.authors && <p className="paper-meta">{asText(paper.authors)}</p>}
    {paper.summary && <p className="paper-summary">{paper.summary}</p>}
    {paper.reason && <p className="paper-reason"><b>推荐理由</b>{paper.reason}</p>}
    <div className="paper-links">{paper.doi && <a href={`https://doi.org/${encodeURIComponent(paper.doi)}`} target="_blank" rel="noreferrer">DOI <ExternalLink size={13} /></a>}{paper.source_url && <a href={paper.source_url} target="_blank" rel="noreferrer">原文 <ExternalLink size={13} /></a>}</div>
  </article>;
}

export function JournalReadingList({ journal }) {
  const [featured, setFeatured] = useState([]);
  const [allPapers, setAllPapers] = useState([]);
  const [view, setView] = useState("featured");
  const [error, setError] = useState("");

  useEffect(() => {
    const featuredUrl = new URL("../../data/papers.json", window.location.href);
    const allUrl = new URL("../../data/all_papers.json", window.location.href);
    Promise.all([fetch(featuredUrl, { cache: "no-store" }), fetch(allUrl, { cache: "no-store" })]).then(async ([featuredResponse, allResponse]) => {
      if (!featuredResponse.ok || !allResponse.ok) throw new Error("期刊论文数据加载失败");
      const [featuredData, allData] = await Promise.all([featuredResponse.json(), allResponse.json()]);
      setFeatured(Array.isArray(featuredData) ? featuredData : []);
      setAllPapers(Array.isArray(allData) ? allData : []);
    }).catch((reason) => setError(reason.message));
  }, []);

  const featuredReading = useMemo(() => sortPapers(featured.filter((paper) => matchesJournal(paper, journal))), [featured, journal]);
  const allReading = useMemo(() => sortPapers(allPapers.filter((paper) => matchesJournal(paper, journal))), [allPapers, journal]);
  const reading = view === "all" ? allReading : featuredReading;
  const groups = useMemo(() => issueGroups(reading), [reading]);
  // Keep the navigation available for online-first papers too. OpenAlex may
  // not assign their final issue until a later publisher update.
  const hasIssues = groups.length > 0;
  const loading = !featured.length && !allPapers.length && !error;

  return <div className="shell">
    <AppSidebar activePath="/journals/" />
    <main className="main journal-reading-main">
      <Link className="back-to-library" href="/journals/"><ArrowLeft size={16} /> 返回期刊书库</Link>
      <header className="journal-reading-header"><p className="eyebrow">期刊精读</p><h1>{journal.name}</h1></header>
      <section className="reading-list" aria-label={`${journal.name} 精读列表`}>
        <div className="section-heading"><div><p className="eyebrow">期刊论文</p><h2>论文列表</h2></div><Tabs value={view} onValueChange={setView}><TabsList aria-label="论文范围"><TabsTrigger value="featured">精选精读 {featuredReading.length}</TabsTrigger><TabsTrigger value="all">全部论文 {allReading.length}</TabsTrigger></TabsList></Tabs></div>
        {error ? <div className="empty-state"><b>论文数据加载失败</b><span>{error}</span></div> : loading ? <div className="empty-state"><b>正在加载论文</b></div> : !reading.length ? <div className="empty-state"><b>{view === "all" ? "本期刊暂未有公开论文" : "本期刊暂未有公开精选"}</b></div> : <div className="issue-reading-layout">
          {hasIssues && <nav className="issue-sidebar" aria-label={`${journal.name} Issue 导航`}><p className="eyebrow">按 Issue 浏览</p><div className="issue-sidebar-list">{groups.map((group) => <a className="issue-sidebar-link" href={`#issue-${group.key}`} key={group.key}><span>{issueLabel(group)}</span><small>{group.papers.length}</small></a>)}</div></nav>}
          <div className="issue-groups">{groups.map((group) => <section className="issue-group" id={`issue-${group.key}`} key={group.key}><header className="issue-group-heading"><h3>{issueLabel(group)}</h3><span>{group.papers.length} 篇</span></header><div className="timeline">{group.papers.map((paper) => <JournalPaperCard paper={paper} key={paper.id || paper.title} />)}</div></section>)}</div>
        </div>}
      </section>
    </main>
  </div>;
}
