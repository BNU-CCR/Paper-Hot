"use client";

import Link from "next/link";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { AppSidebar } from "./app-sidebar";

function asText(value) { return Array.isArray(value) ? value.join(" ") : String(value || ""); }
function sortPapers(papers) { return [...papers].sort((a, b) => Date.parse(b.published_date || 0) - Date.parse(a.published_date || 0)); }
function matchesJournal(paper, journal) {
  const aliases = new Set([journal.name, journal.name.replace(", ", " "), journal.name.replace("Revista Icono 14", "Revista ICONO14"), "Information Communication & Society"]);
  return aliases.has(paper.journal);
}

export function JournalReadingList({ journal }) {
  const [papers, setPapers] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => {
    const url = new URL("../../data/papers.json", window.location.href);
    fetch(url, { cache: "no-store" }).then((response) => {
      if (!response.ok) throw new Error(`精选数据 HTTP ${response.status}`);
      return response.json();
    }).then((data) => setPapers(Array.isArray(data) ? data : [])).catch((reason) => setError(reason.message));
  }, []);
  const reading = useMemo(() => sortPapers(papers.filter((paper) => matchesJournal(paper, journal))), [papers, journal]);
  return <div className="shell">
    <AppSidebar activePath="/journals/" />
    <main className="main journal-reading-main">
      <Link className="back-to-library" href="/journals/"><ArrowLeft size={16} /> 返回期刊书库</Link>
      <header className="journal-reading-header">
        <p className="eyebrow">期刊精读</p><h1>{journal.name}</h1>
        <p>{journal.publisher} · ISSN {journal.issn}。仅展示已公开导出的精选论文，不读取未发布候选、提示词或私有配置。</p>
      </header>
      <section className="reading-list" aria-label={`${journal.name} 精读列表`}>
        <div className="section-heading"><div><p className="eyebrow">公开精选</p><h2>精读列表</h2></div><span className="count">{reading.length} 篇</span></div>
        {error ? <div className="empty-state"><b>精选数据加载失败</b><span>{error}</span></div> : !papers.length ? <div className="empty-state"><b>正在加载精读列表</b></div> : !reading.length ? <div className="empty-state"><b>本期刊暂未有公开精选</b><span>后续自动更新时，新的公开精选会显示在这里。</span></div> : <div className="timeline">{reading.map((paper) => <article className="paper-card" key={paper.id || paper.title}><div className="paper-topline"><span className={`badge ${(paper.relevance || "").toLowerCase()}`}>{paper.score == null ? paper.relevance : `${paper.relevance} ${paper.score}`}</span><time>{paper.published_date || "日期待补充"}</time></div>{paper.source_url ? <a className="paper-title" href={paper.source_url} target="_blank" rel="noreferrer">{paper.title}</a> : <h2 className="paper-title">{paper.title}</h2>}{paper.authors && <p className="paper-meta">{asText(paper.authors)}</p>}{paper.summary && <p className="paper-summary">{paper.summary}</p>}{paper.reason && <p className="paper-reason"><b>推荐理由</b>{paper.reason}</p>}<div className="paper-links">{paper.doi && <a href={`https://doi.org/${encodeURIComponent(paper.doi)}`} target="_blank" rel="noreferrer">DOI <ExternalLink size={13} /></a>}{paper.source_url && <a href={paper.source_url} target="_blank" rel="noreferrer">原文 <ExternalLink size={13} /></a>}</div></article>)}</div>}
      </section>
    </main>
  </div>;
}
