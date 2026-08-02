"use client";

import Link from "next/link";
import { ArrowLeft, CalendarDays, ExternalLink, Layers3 } from "lucide-react";
import { useMemo, useState } from "react";
import type { Journal } from "../types/journal";
import type { Paper } from "../types/paper";
import { AppSidebar } from "./app-sidebar";
import { Tabs, TabsList, TabsTrigger } from "./ui/tabs";

function asText(value: unknown): string { return Array.isArray(value) ? value.join(" ") : String(value || ""); }
function sortPapers(papers: Paper[]): Paper[] { return [...papers].sort((a, b) => Date.parse(b.published_date || "0") - Date.parse(a.published_date || "0")); }
function matchesJournal(paper: Paper, journal: Journal): boolean {
  const aliases = new Set([journal.name, journal.name.replace(", ", " "), journal.name.replace("Revista Icono 14", "Revista ICONO14")]);
  if (journal.name === "Information, Communication & Society") aliases.add("Information Communication & Society");
  return aliases.has(paper.journal ?? "");
}

interface IssueGroup {
  key: string;
  volume: string;
  issue: string;
  papers: Paper[];
}

function issueGroups(papers: Paper[]): IssueGroup[] {
  const groups = new Map<string, IssueGroup>();
  papers.forEach((paper) => {
    const volume = String(paper.volume || "").trim();
    const issue = String(paper.issue || "").trim();
    const key = issue ? `${volume || "no-volume"}-${issue}` : "unassigned";
    if (!groups.has(key)) groups.set(key, { key, volume, issue, papers: [] });
    groups.get(key)!.papers.push(paper);
  });
  return [...groups.values()].sort((a, b) => {
    if (!a.issue) return 1;
    if (!b.issue) return -1;
    return `${b.volume}-${b.issue}`.localeCompare(`${a.volume}-${a.issue}`, "en", { numeric: true });
  });
}

function issueLabel(group: IssueGroup): string {
  if (!group.issue) return "未分期";
  return group.volume ? `Vol. ${group.volume} · Issue ${group.issue}` : `Issue ${group.issue}`;
}

function JournalPaperCard({ paper }: { paper: Paper }) {
  return <article className="paper-card" key={paper.id || paper.title}>
    <div className="paper-topline"><span className={`badge ${(paper.relevance || "").toLowerCase()}`}>{paper.score == null ? paper.relevance : `${paper.relevance} ${paper.score}`}</span><time>{paper.published_date || "日期待补充"}</time></div>
    {paper.source_url ? <a className="paper-title" href={paper.source_url} target="_blank" rel="noreferrer">{paper.title}</a> : <h3 className="paper-title">{paper.title}</h3>}
    {paper.authors && <p className="paper-meta">{asText(paper.authors)}</p>}
    {paper.summary && <p className="paper-summary">{paper.summary}</p>}
    {paper.reason && <p className="paper-reason"><b>推荐理由</b>{paper.reason}</p>}
    <div className="paper-links">{paper.doi && <a href={`https://doi.org/${encodeURIComponent(paper.doi)}`} target="_blank" rel="noreferrer">DOI <ExternalLink size={13} /></a>}{paper.source_url && <a href={paper.source_url} target="_blank" rel="noreferrer">原文 <ExternalLink size={13} /></a>}</div>
  </article>;
}

interface JournalReadingListProps {
  journal: Journal;
  featuredPapers: Paper[];
  allPapers: Paper[];
}

export function JournalReadingList({ journal, featuredPapers, allPapers }: JournalReadingListProps) {
  const [view, setView] = useState("featured");
  const [grouping, setGrouping] = useState("date");

  const featuredReading = useMemo(() => sortPapers(featuredPapers.filter((paper) => matchesJournal(paper, journal))), [featuredPapers, journal]);
  const allReading = useMemo(() => sortPapers(allPapers.filter((paper) => matchesJournal(paper, journal))), [allPapers, journal]);
  const reading = view === "all" ? allReading : featuredReading;
  const groups = useMemo(() => issueGroups(reading), [reading]);

  return <div className="shell">
    <AppSidebar activePath="/journals/" />
    <main className="main journal-reading-main">
      <Link className="back-to-library" href="/journals/"><ArrowLeft size={16} /> 返回期刊书库</Link>
      <header className="journal-reading-header"><h1>{journal.name}</h1></header>
      <section className="reading-list" aria-label={`${journal.name} 精读列表`}>
        <div className="section-heading"><h2>论文列表</h2><div className="reading-actions"><Tabs value={view} onValueChange={setView}><TabsList aria-label="论文范围"><TabsTrigger value="featured">精选精读 {featuredReading.length}</TabsTrigger><TabsTrigger value="all">全部论文 {allReading.length}</TabsTrigger></TabsList></Tabs><Tabs value={grouping} onValueChange={setGrouping}><TabsList aria-label="论文排序"><TabsTrigger value="date"><CalendarDays size={14} aria-hidden="true" />按发布日期</TabsTrigger><TabsTrigger value="issue"><Layers3 size={14} aria-hidden="true" />按 Issue</TabsTrigger></TabsList></Tabs></div></div>
        {!reading.length ? <div className="empty-state"><b>{view === "all" ? "本期刊暂未有公开论文" : "本期刊暂未有公开精选"}</b></div> : grouping === "date" ? <div className="timeline date-feed">{reading.map((paper) => <JournalPaperCard paper={paper} key={paper.id || paper.title} />)}</div> : <div className="issue-reading-layout">
          <nav className="issue-sidebar" aria-label={`${journal.name} Issue 导航`}><div className="issue-sidebar-list">{groups.map((group) => <a className="issue-sidebar-link" href={`#issue-${group.key}`} key={group.key}><span>{issueLabel(group)}</span><small>{group.papers.length}</small></a>)}</div></nav><div className="issue-groups">{groups.map((group) => <section className="issue-group" id={`issue-${group.key}`} key={group.key}><header className="issue-group-heading"><h3>{issueLabel(group)}</h3><span>{group.papers.length} 篇</span></header><div className="timeline">{group.papers.map((paper) => <JournalPaperCard paper={paper} key={paper.id || paper.title} />)}</div></section>)}</div>
        </div>}
      </section>
    </main>
  </div>;
}
