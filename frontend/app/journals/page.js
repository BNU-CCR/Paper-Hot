"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { AppSidebar } from "../../components/app-sidebar";
import { Input } from "../../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { journals } from "../../src/journal-covers";

function BookCover({ journal }) {
  // Keep every cover's title inside the shared cover canvas: longer names scale
  // down instead of creating a taller card or being truncated.
  const titleSize = Math.max(0.58, Math.min(1.08, (1.08 * 42) / journal.name.length));
  return <div className="book-cover" style={{ "--cover": journal.cover.background, "--cover-accent": journal.cover.accent, "--cover-title-size": `${titleSize}rem` }}>
    <span className="cover-issn">ISSN {journal.issn}</span>
    <div className="cover-rule" />
    <span className="cover-title">{journal.name}</span>
    <span className="cover-publisher">{journal.publisher}</span>
  </div>;
}

export default function JournalsPage() {
  const [query, setQuery] = useState("");
  const [publisher, setPublisher] = useState("all");
  const [priority, setPriority] = useState("all");
  const publishers = useMemo(() => [...new Set(journals.map((journal) => journal.publisher))].sort(), []);
  const visible = journals.filter((journal) => {
    const needle = query.trim().toLowerCase();
    return (publisher === "all" || journal.publisher === publisher)
      && (priority === "all" || journal.priority === priority)
      && (!needle || `${journal.name} ${journal.abbr} ${journal.publisher}`.toLowerCase().includes(needle));
  });

  return <div className="shell library-shell">
    <AppSidebar activePath="/journals/" />
    <main className="main library-main">
      <header className="library-header"><div><p className="eyebrow">期刊目录</p><h1>期刊书库</h1></div><div className="library-toolbar shadcn-controls"><label className="search"><span className="sr-only">搜索期刊</span><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索期刊、缩写或出版社" /></label><Select value={publisher} onValueChange={setPublisher}><SelectTrigger aria-label="出版社筛选"><SelectValue placeholder="全部出版社" /></SelectTrigger><SelectContent><SelectItem value="all">全部出版社</SelectItem>{publishers.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select><Tabs value={priority} onValueChange={setPriority}><TabsList aria-label="期刊追踪状态">{[["all", "全部"], ["core", "核心"], ["watch", "关注"], ["skip", "存档"]].map(([value, label]) => <TabsTrigger key={value} value={value}>{label}</TabsTrigger>)}</TabsList></Tabs></div></header>
      <section className="library-heading"><span>共 {visible.length} 本期刊</span><span>点击书封访问出版社</span></section>
      <section className="bookshelf" aria-label="期刊书架">{visible.map((journal) => <Link key={journal.abbr} className="book" href={`/journals/${journal.slug}/`} aria-label={`查看 ${journal.name} 的精读列表`}><BookCover journal={journal} /><span className="book-caption"><b>{journal.name}</b><span>{journal.publisher} · {journal.priority === "core" ? "核心追踪" : journal.priority === "watch" ? "关注追踪" : "存档期刊"}</span></span></Link>)}</section>
      {!visible.length && <div className="empty-state"><b>没有匹配的期刊</b><span>试试清除搜索词或调整筛选条件。</span></div>}
      <p className="library-note">点击书封查看该期刊已公开导出的精选精读；书封视觉资产与期刊元数据集中维护在 <code>frontend/src/journal-covers.js</code>。</p>
    </main>
  </div>;
}
