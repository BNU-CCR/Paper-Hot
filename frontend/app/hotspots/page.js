"use client";

import { useEffect, useMemo, useState } from "react";
import { AppSidebar } from "../../components/app-sidebar";

function asText(value) { return Array.isArray(value) ? value.join(" ") : String(value || ""); }
function displayPeriod(start, end) { return start && end ? `${start.replaceAll("-", ".")} – ${end.replaceAll("-", ".")}` : "近一个月"; }

function PaperCard({ paper }) {
  return <article className="paper-card"><div className="paper-topline"><span className={`badge ${(paper.relevance || "").toLowerCase()}`}>{paper.relevance || "精选"}</span><time>{paper.published_date || "日期待补充"}</time></div>{paper.source_url ? <a className="paper-title" href={paper.source_url} target="_blank" rel="noreferrer">{paper.title}</a> : <h3 className="paper-title">{paper.title}</h3>}<p className="paper-meta">{[asText(paper.authors), paper.journal].filter(Boolean).join(" · ")}</p>{paper.summary && <p className="paper-summary">{paper.summary}</p>}<div className="paper-tags">{(paper.tags || []).map((tag) => <span className="tag" key={tag}>{tag}</span>)}</div></article>;
}

export default function HotspotsPage() {
  const [hotspots, setHotspots] = useState(null);
  const [papers, setPapers] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => { Promise.all([fetch("../data/hotspots.json", { cache: "no-store" }), fetch("../data/papers.json", { cache: "no-store" })]).then(async ([hotspotResponse, paperResponse]) => { if (!hotspotResponse.ok || !paperResponse.ok) throw new Error("热点数据加载失败"); setHotspots(await hotspotResponse.json()); setPapers(await paperResponse.json()); }).catch((reason) => setError(reason.message)); }, []);
  const byId = useMemo(() => new Map(papers.map((paper) => [Number(paper.id), paper])), [papers]);
  const topics = Array.isArray(hotspots?.topics) ? hotspots.topics : [];
  return <div className="shell"><AppSidebar activePath="/hotspots/" /><main className="main"><section className="hero"><div className="eyebrow">LLM 月度聚合</div><div className="headline"><div><h1>当期热点</h1><p>从近一个月已公开的计算传播论文中识别主要研究议题，并关联可直接阅读的论文。</p></div><div className="stats"><span>{topics.length} 个热点</span><span>{hotspots?.source_paper_count || 0} 篇论文</span></div></div></section>{error ? <div className="empty-state"><b>热点数据加载失败</b><span>{error}</span></div> : !topics.length ? <div className="empty-state"><b>当期热点暂未生成</b><span>下一次自动更新会生成新的月度议题。</span></div> : <section className="hotspot-feed"><div className="section-heading"><div><p className="eyebrow">{displayPeriod(hotspots.period_start, hotspots.period_end)}</p><h2>研究议题</h2></div><span className="count">仅基于公开论文</span></div><div className="hotspot-grid">{topics.map((topic) => <article className="hotspot-topic" key={topic.title}><header><h3>{topic.title}</h3><p>{topic.description}</p></header><div className="hotspot-papers">{(topic.paper_ids || []).map((id) => byId.get(Number(id))).filter(Boolean).map((paper) => <PaperCard key={paper.id} paper={paper} />)}</div></article>)}</div></section>}</main></div>;
}
