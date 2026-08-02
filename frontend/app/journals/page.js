"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { journals } from "../../src/journal-covers";

const GITHUB_URL = "https://github.com/BNU-CCR/Paper-Hot";

function BookCover({ journal }) {
  const titleSize = Math.max(0.72, Math.min(1.12, (1.12 * 48) / journal.name.length));
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
    <aside className="sidebar"><Link className="brand" href="/"><span>Paper</span><i /><span>HOT</span></Link><nav aria-label="主导航"><Link href="/">精选论文</Link><Link className="active" href="/journals/">期刊书库</Link><Link href="/about/">关于项目</Link></nav><a className="github-link" href={GITHUB_URL} target="_blank" rel="noreferrer">GitHub ↗</a></aside>
    <main className="main library-main">
      <header className="library-header"><div><p className="eyebrow">期刊目录</p><h1>期刊书库</h1></div><div className="library-toolbar"><label className="search"><span className="sr-only">搜索期刊</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索期刊、缩写或出版社" /></label><label className="select-label">出版社<select value={publisher} onChange={(event) => setPublisher(event.target.value)}><option value="all">全部出版社</option>{publishers.map((item) => <option key={item}>{item}</option>)}</select></label><div className="segmented library-priority">{[["all", "全部"], ["core", "核心"], ["watch", "关注"], ["skip", "存档"]].map(([value, label]) => <button key={value} className={priority === value ? "active" : ""} onClick={() => setPriority(value)}>{label}</button>)}</div></div></header>
      <section className="library-heading"><span>共 {visible.length} 本期刊</span><span>点击书封访问出版社</span></section>
      <section className="bookshelf" aria-label="期刊书架">{visible.map((journal) => <a key={journal.abbr} className="book" href={journal.publisherUrl} target="_blank" rel="noreferrer" aria-label={`访问 ${journal.name} 出版社页面`}><BookCover journal={journal} /><span className="book-caption"><b>{journal.name}</b><span>{journal.publisher} · {journal.priority === "core" ? "核心追踪" : journal.priority === "watch" ? "关注追踪" : "存档期刊"}</span></span></a>)}</section>
      {!visible.length && <div className="empty-state"><b>没有匹配的期刊</b><span>试试清除搜索词或调整筛选条件。</span></div>}
      <p className="library-note">书封视觉资产与期刊元数据集中维护在 <code>frontend/src/journal-covers.js</code>；出版机构名称与 ISSN 来自项目的期刊追踪配置。</p>
    </main>
  </div>;
}
