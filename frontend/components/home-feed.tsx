"use client";

import { useMemo, useState } from "react";
import Masonry from "react-masonry-css";
import { Building2, ChevronDown, ExternalLink, LayoutGrid, ListChecks, Rows3 } from "lucide-react";
import type { Paper } from "../types/paper";
import { Button } from "./ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "./ui/collapsible";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "./ui/dialog";
import { Input } from "./ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Tabs, TabsList, TabsTrigger } from "./ui/tabs";
import { LanguageToggle, type PaperLanguage } from "./language-toggle";

const masonryColumns = { default: 3, 1080: 2, 680: 1 };

function asText(value: unknown): string {
  return Array.isArray(value) ? value.join(" ") : String(value || "");
}

function displayAuthors(value: unknown): string {
  return Array.isArray(value) ? value.filter(Boolean).join(", ") : String(value || "");
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

function PaperCard({ paper, featured, language, onOpen }: { paper: Paper; featured?: boolean; language: PaperLanguage; onOpen: (paper: Paper) => void }) {
  const relevance = paper.relevance || "Unrated";
  const score = paper.score == null ? relevance : `${relevance} ${paper.score}`;
  // In the featured feed every paper is High, so the relevance badge is
  // redundant — surface the method label there instead.
  const topline = featured
    ? (paper.method ? <span className="tag method-tag" title="研究方法">{paper.method}</span> : <span className={`badge ${relevance.toLowerCase()}`}>{relevance}</span>)
    : <span className={`badge ${relevance.toLowerCase()}`}>{score}</span>;
  const title = language === "zh" && paper.title_zh ? paper.title_zh : paper.title;
  return (
    <article
      className="paper-card paper-card-interactive"
      role="button"
      tabIndex={0}
      aria-label={`查看论文详情：${title || "未命名论文"}`}
      onClick={() => onOpen(paper)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onOpen(paper);
        }
      }}
    >
      <div className="paper-topline">
        {topline}
        <time>{paper.published_date || "日期待补充"}</time>
      </div>
      <h3 className="paper-title">{title || "Untitled paper"}</h3>
      {(paper.authors || paper.journal) && <p className="paper-meta">{[displayAuthors(paper.authors), paper.journal].filter(Boolean).join(" · ")}</p>}
      {paper.summary && <p className="paper-summary">{paper.summary}</p>}
      {!featured && paper.reason && <p className="paper-reason">{paper.reason}</p>}
      <div className="paper-tags">
        {(paper.tags || []).map((tag) => <span key={tag} className="tag">{tag}</span>)}
        {!featured && paper.method && <span className="tag method-tag" title="研究方法">{paper.method}</span>}
      </div>
      <div className="paper-links">
        {paper.doi && <a href={`https://doi.org/${encodeURIComponent(paper.doi)}`} target="_blank" rel="noreferrer" onClick={(event) => event.stopPropagation()}>DOI</a>}
        {paper.source_url && <a href={paper.source_url} target="_blank" rel="noreferrer" onClick={(event) => event.stopPropagation()}>原文</a>}
      </div>
    </article>
  );
}

function PaperDetailDialog({ paper, language, onOpenChange }: { paper: Paper | null; language: PaperLanguage; onOpenChange: (open: boolean) => void }) {
  if (!paper) return null;
  const publication = [paper.journal, paper.volume && `Vol. ${paper.volume}`, paper.issue && `Issue ${paper.issue}`].filter(Boolean).join(" · ");
  const title = language === "zh" && paper.title_zh ? paper.title_zh : paper.title;
  const abstract = language === "zh" && paper.abstract_zh ? paper.abstract_zh : paper.abstract;
  return (
    <Dialog open={Boolean(paper)} onOpenChange={onOpenChange}>
      <DialogContent>
        <div className="paper-dialog-main">
          <div className="paper-dialog-kicker">
            {paper.method && <span className="tag method-tag">{paper.method}</span>}
            <time>{displayDate(paper.published_date || "")}</time>
          </div>
          <DialogTitle className="paper-dialog-title">{title || "Untitled paper"}</DialogTitle>
          {(paper.authors || publication) && <p className="paper-dialog-meta">{[displayAuthors(paper.authors), publication].filter(Boolean).join(" · ")}</p>}
          {abstract && (
            <section className="paper-dialog-section">
              <h2>摘要</h2>
              <DialogDescription className="paper-dialog-abstract">{abstract}</DialogDescription>
            </section>
          )}
        </div>
        <aside className="paper-dialog-aside">
          {paper.summary && <section className="paper-dialog-section"><h2>内容摘要</h2><p>{paper.summary}</p></section>}
          {!paper.summary && <DialogDescription className="sr-only">论文详情与原文入口</DialogDescription>}
          {(paper.tags?.length || paper.method) && (
            <section className="paper-dialog-section">
              <h2>主题与方法</h2>
              <div className="paper-tags">
                {(paper.tags || []).map((tag) => <span key={tag} className="tag">{tag}</span>)}
                {paper.method && <span className="tag method-tag">{paper.method}</span>}
              </div>
            </section>
          )}
          {paper.institutions && paper.institutions.length > 0 && (
            <section className="paper-dialog-section">
              <h2 className="paper-dialog-section-title"><Building2 size={14} aria-hidden="true" />作者机构</h2>
              <ul className="paper-dialog-institutions">
                {paper.institutions.map((institution) => <li key={institution}>{institution}</li>)}
              </ul>
            </section>
          )}
          <div className="paper-dialog-actions">
            {paper.doi && <a href={`https://doi.org/${encodeURIComponent(paper.doi)}`} target="_blank" rel="noreferrer">查看 DOI <ExternalLink size={14} aria-hidden="true" /></a>}
            {paper.source_url && <a className="primary" href={paper.source_url} target="_blank" rel="noreferrer">阅读原文 <ExternalLink size={14} aria-hidden="true" /></a>}
          </div>
        </aside>
      </DialogContent>
    </Dialog>
  );
}

interface HomeFeedProps {
  featured: Paper[];
  allPapers: Paper[];
}

function TopicButton({ item, count, selected, onClick }: { item: string; count: number; selected: boolean; onClick: () => void }) {
  return (
    <Button
      variant={selected ? "secondary" : "outline"}
      size="sm"
      className="topic-button"
      onClick={onClick}
      aria-pressed={selected}
    >
      <span>{item}</span>
      <span className="topic-count">{count}</span>
    </Button>
  );
}

export function HomeFeed({ featured, allPapers }: HomeFeedProps) {
  const [mode, setMode] = useState("featured");
  const [relevance, setRelevance] = useState("all");
  const [journal, setJournal] = useState("all");
  const [method, setMethod] = useState("all");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [multiSelect, setMultiSelect] = useState(false);
  const [query, setQuery] = useState("");
  const [tagsOpen, setTagsOpen] = useState(false);
  const [layout, setLayout] = useState("auto");
  const [language, setLanguage] = useState<PaperLanguage>("original");
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);

  const source = mode === "all" ? allPapers : featured;
  const journals = useMemo(() => [...new Set(source.map((paper) => paper.journal).filter((item): item is string => Boolean(item)))].sort((a, b) => a.localeCompare(b, "zh-CN")), [source]);
  const methods = useMemo(() => [...new Set(source.map((paper) => paper.method).filter((m): m is string => Boolean(m)))].sort((a, b) => a.localeCompare(b, "zh-CN")), [source]);
  const tags = useMemo(() => {
    const count = new Map<string, number>();
    source.forEach((paper) => (paper.tags || []).forEach((item) => count.set(item, (count.get(item) || 0) + 1)));
    return [...count.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "zh-CN"));
  }, [source]);
  const papers = useMemo(() => sortPapers(source.filter((paper) => {
    if (relevance !== "all" && paper.relevance !== relevance) return false;
    if (journal !== "all" && paper.journal !== journal) return false;
    if (method !== "all" && paper.method !== method) return false;
    if (selectedTags.length && !(paper.tags || []).some((item) => selectedTags.some((selected) => item.toLowerCase() === selected.toLowerCase()))) return false;
    const needle = query.trim().toLowerCase();
    return !needle || [paper.title, paper.title_zh, paper.abstract_zh, paper.summary, paper.reason, paper.journal, asText(paper.authors), asText(paper.tags), paper.method || ""].join(" ").toLowerCase().includes(needle);
  })), [source, relevance, journal, method, selectedTags, query]);

  const toggleTag = (item: string) => {
    setSelectedTags((current) => {
      const selected = current.includes(item);
      if (!multiSelect) return selected ? [] : [item];
      return selected ? current.filter((tag) => tag !== item) : [...current, item];
    });
  };

  return (
    <div className="main">
        <section className="hero home-hero">
          <div className="headline"><h1>Paper HOT</h1></div>
          <div className="toolbar shadcn-controls">
            <Tabs value={mode} onValueChange={(value) => { setMode(value); if (value === "featured") setRelevance("all"); }}><TabsList aria-label="数据范围"><TabsTrigger value="featured">精选</TabsTrigger><TabsTrigger value="all">期刊全量</TabsTrigger></TabsList></Tabs>
            {mode === "all" && <Tabs value={relevance} onValueChange={setRelevance}><TabsList aria-label="相关性筛选"><TabsTrigger value="all">全部</TabsTrigger><TabsTrigger value="High">高相关</TabsTrigger><TabsTrigger value="Medium">其他相似文章</TabsTrigger></TabsList></Tabs>}<Select value={journal} onValueChange={setJournal}><SelectTrigger aria-label="期刊筛选"><SelectValue placeholder="全部期刊" /></SelectTrigger><SelectContent><SelectItem value="all">全部期刊</SelectItem>{journals.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select><Select value={method} onValueChange={setMethod}><SelectTrigger aria-label="方法筛选"><SelectValue placeholder="全部方法" /></SelectTrigger><SelectContent><SelectItem value="all">全部方法</SelectItem>{methods.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select><label className="search"><span className="sr-only">搜索论文</span><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索标题、摘要、作者、期刊、方法、标签" /></label><LanguageToggle value={language} onValueChange={setLanguage} />
          </div>
        </section>

        <Collapsible className="topics-panel" open={tagsOpen} onOpenChange={setTagsOpen}>
          <div className="section-heading"><h2>主题标签</h2><div className="section-actions"><CollapsibleTrigger asChild><Button variant="ghost" size="sm"><ChevronDown size={14} aria-hidden="true" className={`chevron-icon ${tagsOpen ? "open" : ""}`} />{tagsOpen ? "收起标签" : `展开全部 ${tags.length} 个标签`}</Button></CollapsibleTrigger><Button variant={multiSelect ? "secondary" : "ghost"} size="sm" aria-pressed={multiSelect} onClick={() => { setMultiSelect((current) => !current); if (multiSelect) setSelectedTags((current) => current.slice(0, 1)); }}><ListChecks aria-hidden="true" />多选</Button>{selectedTags.length > 0 && <Button variant="ghost" size="sm" onClick={() => setSelectedTags([])} aria-label="清除所有主题筛选">清除筛选</Button>}</div></div>
          <div className="tag-cloud">{tags.slice(0, 12).map(([item, count]) => <TopicButton key={item} item={item} count={count} selected={selectedTags.includes(item)} onClick={() => toggleTag(item)} />)}</div>
          <CollapsibleContent><div className="tag-cloud extra-tags">{tags.slice(12).map(([item, count]) => <TopicButton key={item} item={item} count={count} selected={selectedTags.includes(item)} onClick={() => toggleTag(item)} />)}</div></CollapsibleContent>
          {selectedTags.length > 0 && <div className="topic-filter-status" role="status" aria-live="polite"><span>当前筛选</span><b>{selectedTags.join("、")}</b><span>{papers.length} 篇</span></div>}
        </Collapsible>

        <section className="feed"><div className="section-heading"><h2>{mode === "featured" ? "最新精选" : "期刊全量更新"}</h2><div className="feed-heading-actions"><span className="count">{papers.length} 篇</span>{mode === "featured" && <Tabs value={layout} onValueChange={setLayout}><TabsList aria-label="卡片布局" className="layout-tabs"><TabsTrigger value="single" aria-label="单栏布局" title="单栏布局"><Rows3 aria-hidden="true" /></TabsTrigger><TabsTrigger value="auto" aria-label="自动多栏布局" title="自动多栏布局"><LayoutGrid aria-hidden="true" /></TabsTrigger></TabsList></Tabs>}</div></div>
          {papers.length === 0 ? <div className="empty-state"><b>没有匹配当前条件的论文</b><span>可以调整期刊、主题、相关性或搜索词。</span></div> : mode === "featured" ? layout === "single" ? <div className="paper-single-column">{papers.map((paper) => <PaperCard key={paper.id || `${paper.title}-${paper.published_date}`} paper={paper} featured language={language} onOpen={setSelectedPaper} />)}</div> : <Masonry breakpointCols={masonryColumns} className="paper-masonry" columnClassName="paper-masonry-column">{papers.map((paper) => <PaperCard key={paper.id || `${paper.title}-${paper.published_date}`} paper={paper} featured language={language} onOpen={setSelectedPaper} />)}</Masonry> : <div className="timeline">{Object.entries(papers.reduce<Record<string, Paper[]>>((groups, paper) => { const key = paper.published_date || "日期待补充"; (groups[key] ||= []).push(paper); return groups; }, {})).map(([date, group]) => <section className="day-group" key={date}><h3>{displayDate(date)}</h3>{group.map((paper) => <PaperCard key={paper.id || `${paper.title}-${paper.published_date}`} paper={paper} language={language} onOpen={setSelectedPaper} />)}</section>)}</div>}
        </section>
        <PaperDetailDialog paper={selectedPaper} language={language} onOpenChange={(open) => { if (!open) setSelectedPaper(null); }} />
    </div>
  );
}
