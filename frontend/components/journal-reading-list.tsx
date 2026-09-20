"use client";

import Link from "next/link";
import { ArrowLeft, CalendarDays, Download, ExternalLink, Layers3 } from "lucide-react";
import { useMemo, useState } from "react";
import * as XLSX from "xlsx";
import type { Journal } from "../types/journal";
import type { Paper } from "../types/paper";
import { Button } from "./ui/button";
import { Tabs, TabsList, TabsTrigger } from "./ui/tabs";
import { LanguageToggle, type PaperLanguage } from "./language-toggle";

function asText(value: unknown): string { return Array.isArray(value) ? value.join(", ") : String(value || ""); }
function paperTime(paper: Paper): number {
  const time = Date.parse(paper.published_date || "");
  return Number.isFinite(time) ? time : 0;
}
function sortPapers(papers: Paper[]): Paper[] { return [...papers].sort((a, b) => paperTime(b) - paperTime(a)); }

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
  groups.forEach((group) => { group.papers = sortPapers(group.papers); });
  return [...groups.values()].sort((a, b) => {
    const latestDifference = paperTime(b.papers[0]) - paperTime(a.papers[0]);
    if (latestDifference !== 0) return latestDifference;
    if (!a.issue && b.issue) return 1;
    if (!b.issue && a.issue) return -1;
    return `${b.volume}-${b.issue}`.localeCompare(`${a.volume}-${a.issue}`, "en", { numeric: true });
  });
}

function issueLabel(group: IssueGroup): string {
  if (!group.issue) return "未分期";
  return group.volume ? `Vol. ${group.volume} · Issue ${group.issue}` : `Issue ${group.issue}`;
}

function safeFilePart(value: string): string {
  return value.replace(/[\\/:*?"<>|]/g, "-").replace(/\s+/g, " ").trim();
}

function exportPapers(papers: Paper[], journalName: string, scope: string): void {
  const rows = papers.map((paper) => ({
    "英文标题": paper.title || "",
    "中文标题": paper.title_zh || "",
    "作者": asText(paper.authors),
    "作者机构": asText(paper.institutions),
    "期刊": paper.journal || journalName,
    "发布日期": paper.published_date || "",
    "卷": paper.volume || "",
    "期": paper.issue || "",
    "研究方法": paper.method || "",
    "相关性": paper.relevance || "",
    "评分": paper.score ?? "",
    "主题标签": (paper.tags || []).join("；"),
    "中文摘要": paper.abstract_zh || "",
    "原文摘要": paper.abstract || "",
    "推荐摘要": paper.summary || "",
    "推荐理由": paper.reason || "",
    "DOI": paper.doi || "",
    "原文链接": paper.source_url || "",
  }));
  const worksheet = XLSX.utils.json_to_sheet(rows);
  worksheet["!cols"] = [
    { wch: 46 }, { wch: 42 }, { wch: 28 }, { wch: 32 }, { wch: 28 }, { wch: 12 },
    { wch: 8 }, { wch: 8 }, { wch: 14 }, { wch: 10 }, { wch: 8 }, { wch: 24 },
    { wch: 60 }, { wch: 60 }, { wch: 54 }, { wch: 54 }, { wch: 28 }, { wch: 42 },
  ];
  worksheet["!autofilter"] = { ref: worksheet["!ref"] || "A1:R1" };
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "论文列表");
  const date = new Date().toISOString().slice(0, 10);
  const fileName = `${safeFilePart(journalName)}-${scope}-${date}.xlsx`;
  const bytes = XLSX.write(workbook, { bookType: "xlsx", type: "array", compression: true });
  const url = URL.createObjectURL(new Blob([bytes], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function JournalPaperCard({ paper, featured, language }: { paper: Paper; featured?: boolean; language: PaperLanguage }) {
  const relevance = paper.relevance || "Unrated";
  const score = paper.score == null ? relevance : `${relevance} ${paper.score}`;
  const topline = featured
    ? (paper.method ? <span className="tag method-tag" title="研究方法">{paper.method}</span> : <span className={`badge ${(paper.relevance || "").toLowerCase()}`}>{paper.relevance || "精选"}</span>)
    : <span className={`badge ${(paper.relevance || "").toLowerCase()}`}>{score}</span>;
  const title = language === "zh" && paper.title_zh ? paper.title_zh : paper.title;
  return <article className="paper-card" key={paper.id || paper.title}>
    <div className="paper-topline">{topline}<time>{paper.published_date || "日期待补充"}</time></div>
    {paper.source_url ? <a className="paper-title" href={paper.source_url} target="_blank" rel="noreferrer">{title}</a> : <h3 className="paper-title">{title}</h3>}
    {paper.authors && <p className="paper-meta">{asText(paper.authors)}</p>}
    {paper.summary && <p className="paper-summary">{paper.summary}</p>}
    {!featured && paper.reason && <p className="paper-reason">{paper.reason}</p>}
    {(paper.tags || []).length > 0 && <div className="paper-tags">{(paper.tags || []).map((tag) => <span className="tag" key={tag}>{tag}</span>)}{!featured && paper.method && <span className="tag method-tag" title="研究方法">{paper.method}</span>}</div>}
    <div className="paper-links">{paper.doi && <a href={`https://doi.org/${encodeURIComponent(paper.doi)}`} target="_blank" rel="noreferrer">DOI <ExternalLink size={13} /></a>}{paper.source_url && <a href={paper.source_url} target="_blank" rel="noreferrer">原文 <ExternalLink size={13} /></a>}</div>
  </article>;
}

interface JournalReadingListProps {
  journal: Journal;
  /** Already filtered to this journal on the server. */
  featuredPapers: Paper[];
  allPapers: Paper[];
}

export function JournalReadingList({ journal, featuredPapers, allPapers }: JournalReadingListProps) {
  const [view, setView] = useState("featured");
  const [grouping, setGrouping] = useState("date");
  const [language, setLanguage] = useState<PaperLanguage>("original");
  const [exportFailed, setExportFailed] = useState(false);

  const featuredReading = useMemo(() => sortPapers(featuredPapers), [featuredPapers]);
  const allReading = useMemo(() => sortPapers(allPapers), [allPapers]);
  const reading = view === "all" ? allReading : featuredReading;
  const groups = useMemo(() => issueGroups(reading), [reading]);
  const exportCurrentView = () => {
    setExportFailed(false);
    try {
      exportPapers(reading, journal.name, view === "all" ? "全部论文" : "精选精读");
    } catch (error) {
      console.error("导出期刊论文失败", error);
      setExportFailed(true);
    }
  };

  return <div className="main journal-reading-main">
      <Link className="back-to-library" href="/journals/"><ArrowLeft size={16} /> 返回期刊书库</Link>
      <header className="journal-reading-header"><h1>{journal.name}</h1></header>
      <section className="reading-list" aria-label={`${journal.name} 精读列表`}>
        <div className="section-heading"><h2>论文列表</h2><div className="reading-actions"><Tabs value={view} onValueChange={setView}><TabsList aria-label="论文范围"><TabsTrigger value="featured">精选精读 {featuredReading.length}</TabsTrigger><TabsTrigger value="all">全部论文 {allReading.length}</TabsTrigger></TabsList></Tabs><Tabs value={grouping} onValueChange={setGrouping}><TabsList aria-label="论文排序"><TabsTrigger value="date"><CalendarDays size={14} aria-hidden="true" />按发布日期</TabsTrigger><TabsTrigger value="issue"><Layers3 size={14} aria-hidden="true" />按 Issue</TabsTrigger></TabsList></Tabs><LanguageToggle value={language} onValueChange={setLanguage} /><Button variant="outline" size="sm" onClick={exportCurrentView} disabled={!reading.length}><Download aria-hidden="true" />导出 XLSX</Button>{exportFailed && <span className="export-error" role="status">导出失败，请重试</span>}</div></div>
        {!reading.length ? <div className="empty-state"><b>{view === "all" ? "本期刊暂未有公开论文" : "本期刊暂未有公开精选"}</b></div> : grouping === "date" ? <div className="timeline date-feed">{reading.map((paper) => <JournalPaperCard paper={paper} key={paper.id || paper.title} featured={view === "featured"} language={language} />)}</div> : <div className="issue-reading-layout">
          <nav className="issue-sidebar" aria-label={`${journal.name} Issue 导航`}><div className="issue-sidebar-list">{groups.map((group) => <a className="issue-sidebar-link" href={`#issue-${group.key}`} key={group.key}><span>{issueLabel(group)}</span><small>{group.papers.length}</small></a>)}</div></nav><div className="issue-groups">{groups.map((group) => <section className="issue-group" id={`issue-${group.key}`} key={group.key}><header className="issue-group-heading"><h3>{issueLabel(group)}</h3><span>{group.papers.length} 篇</span></header><div className="timeline">{group.papers.map((paper) => <JournalPaperCard paper={paper} key={paper.id || paper.title} featured={view === "featured"} language={language} />)}</div></section>)}</div>
        </div>}
      </section>
  </div>;
}
