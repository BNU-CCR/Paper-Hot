"use client";

import { useMemo, useState } from "react";
import Masonry from "react-masonry-css";
import { ChevronDown } from "lucide-react";
import type { Paper } from "../types/paper";
import { Button } from "./ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "./ui/collapsible";
import { Input } from "./ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Tabs, TabsList, TabsTrigger } from "./ui/tabs";

const masonryColumns = { default: 3, 1080: 2, 680: 1 };

function asText(value: unknown): string {
  return Array.isArray(value) ? value.join(" ") : String(value || "");
}

function sortPapers(papers: Paper[]): Paper[] {
  return [...papers].sort((a, b) => {
    const aDate = Date.parse(a.published_date || "");
    const bDate = Date.parse(b.published_date || "");
    if (Number.isFinite(aDate) && Number.isFinite(bDate) && aDate !== bDate) return bDate - aDate;
    if (Number.isFinite(aDate) !== Number.isFinite(bDate)) return Number.isFinite(aDate) ? -1 : 1;
    return Number(b.id || 0) - Number(a.id || 0);
  });
}

function displayDate(value: string): string {
  if (!value) return "日期待补充";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric", weekday: "short" });
}

function PaperCard({ paper }: { paper: Paper }) {
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

interface HomeFeedProps {
  featured: Paper[];
  allPapers: Paper[];
}

export function HomeFeed({ featured, allPapers }: HomeFeedProps) {
  const [mode, setMode] = useState("featured");
  const [relevance, setRelevance] = useState("all");
  const [journal, setJournal] = useState("all");
  const [tag, setTag] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [tagsOpen, setTagsOpen] = useState(false);

  const source = mode === "all" ? allPapers : featured;
  const journals = useMemo(() => [...new Set(source.map((paper) => paper.journal).filter((item): item is string => Boolean(item)))].sort((a, b) => a.localeCompare(b, "zh-CN")), [source]);
  const tags = useMemo(() => {
    const count = new Map<string, number>();
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
    <div className="main">
        <section className="hero home-hero">
          <div className="headline"><h1>Paper HOT</h1></div>
          <div className="toolbar shadcn-controls">
            <Tabs value={mode} onValueChange={(value) => { setMode(value); if (value === "featured") setRelevance("all"); }}><TabsList aria-label="数据范围"><TabsTrigger value="featured">精选</TabsTrigger><TabsTrigger value="all">期刊全量</TabsTrigger></TabsList></Tabs>
            {mode === "all" && <Tabs value={relevance} onValueChange={setRelevance}><TabsList aria-label="相关性筛选"><TabsTrigger value="all">全部</TabsTrigger><TabsTrigger value="High">高相关</TabsTrigger><TabsTrigger value="Medium">其他相似文章</TabsTrigger></TabsList></Tabs>}<Select value={journal} onValueChange={setJournal}><SelectTrigger aria-label="期刊筛选"><SelectValue placeholder="全部期刊" /></SelectTrigger><SelectContent><SelectItem value="all">全部期刊</SelectItem>{journals.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select><label className="search"><span className="sr-only">搜索论文</span><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索标题、摘要、作者、期刊、标签" /></label>
          </div>
        </section>

        <Collapsible className="topics-panel" open={tagsOpen} onOpenChange={setTagsOpen}>
          <div className="section-heading"><h2>主题标签</h2><div className="section-actions"><CollapsibleTrigger asChild><Button variant="ghost" size="sm"><ChevronDown size={14} aria-hidden="true" className={`chevron-icon ${tagsOpen ? "open" : ""}`} />{tagsOpen ? "收起标签" : `展开全部 ${tags.length} 个标签`}</Button></CollapsibleTrigger>{tag && <Button variant="ghost" size="sm" onClick={() => setTag(null)} aria-label={`清除主题筛选：${tag}`}>清除筛选</Button>}</div></div>
          <div className="tag-cloud">{tags.slice(0, 12).map(([item, count]) => <Button key={item} variant={tag === item ? "default" : "outline"} size="sm" className="tag" onClick={() => setTag(tag === item ? null : item)} aria-pressed={tag === item}>{item}<small>{count}</small></Button>)}</div>
          <CollapsibleContent><div className="tag-cloud extra-tags">{tags.slice(12).map(([item, count]) => <Button key={item} variant={tag === item ? "default" : "outline"} size="sm" className="tag" onClick={() => setTag(tag === item ? null : item)} aria-pressed={tag === item}>{item}<small>{count}</small></Button>)}</div></CollapsibleContent>
          {tag && <div className="topic-filter-status" role="status" aria-live="polite"><span>当前筛选</span><b>{tag}</b><span>{papers.length} 篇</span></div>}
        </Collapsible>

        <section className="feed"><div className="section-heading"><h2>{mode === "featured" ? "最新精选" : "期刊全量更新"}</h2><span className="count">{papers.length} 篇</span></div>
          {papers.length === 0 ? <div className="empty-state"><b>没有匹配当前条件的论文</b><span>可以调整期刊、主题、相关性或搜索词。</span></div> : mode === "featured" ? <Masonry breakpointCols={masonryColumns} className="paper-masonry" columnClassName="paper-masonry-column">{papers.map((paper) => <PaperCard key={paper.id || `${paper.title}-${paper.published_date}`} paper={paper} />)}</Masonry> : <div className="timeline">{Object.entries(papers.reduce<Record<string, Paper[]>>((groups, paper) => { const key = paper.published_date || "日期待补充"; (groups[key] ||= []).push(paper); return groups; }, {})).map(([date, group]) => <section className="day-group" key={date}><h3>{displayDate(date)}</h3>{group.map((paper) => <PaperCard key={paper.id || `${paper.title}-${paper.published_date}`} paper={paper} />)}</section>)}</div>}
        </section>
    </div>
  );
}
