import type { HotspotTopic } from "../../types/hotspot";
import type { Paper } from "../../types/paper";
import { AppSidebar } from "../../components/app-sidebar";
import { getFeaturedPapers, getHotspots, getHotspotGraph, getHotspotTrends, getHotspotManifest } from "../../lib/data";
import { HotspotPageClient } from "./page-client";

function asText(value: unknown): string { return Array.isArray(value) ? value.join(" ") : String(value || ""); }
function displayPeriod(start?: string, end?: string): string { return start && end ? `${start.replaceAll("-", ".")} – ${end.replaceAll("-", ".")}` : "近一个月"; }

function PaperCard({ paper }: { paper: Paper }) {
  return <article className="paper-card"><div className="paper-topline"><span className={`badge ${(paper.relevance || "").toLowerCase()}`}>{paper.relevance || "精选"}</span><time>{paper.published_date || "日期待补充"}</time></div>{paper.source_url ? <a className="paper-title" href={paper.source_url} target="_blank" rel="noreferrer">{paper.title}</a> : <h3 className="paper-title">{paper.title}</h3>}<p className="paper-meta">{[asText(paper.authors), paper.journal].filter(Boolean).join(" · ")}</p>{paper.summary && <p className="paper-summary">{paper.summary}</p>}<div className="paper-tags">{(paper.tags || []).map((tag) => <span className="tag" key={tag}>{tag}</span>)}</div></article>;
}

export default function HotspotsPage() {
  const hotspots = getHotspots();
  const papers = getFeaturedPapers();
  const graph = getHotspotGraph();
  const trends = getHotspotTrends();
  const manifest = getHotspotManifest();

  const byId = new Map(papers.map((paper) => [Number(paper.id), paper]));
  const topics: HotspotTopic[] = Array.isArray(hotspots?.topics) ? hotspots.topics : [];

  const hasGraph = graph.nodes.length > 0;
  const hasTrends = trends.length > 0;

  const topicCount = hasGraph ? manifest.topic_count : topics.length;
  const paperCount = hasGraph ? manifest.paper_count : (hotspots?.source_paper_count || 0);

  return (
    <div className="shell">
      <AppSidebar activePath="/hotspots/" />
      <main className="main">
        <section className="hero">
          <div className="headline">
            <div>
              <h1>当期热点</h1>
              <p>从近一个月已公开的计算传播论文中识别主要研究议题，并关联可直接阅读的论文。</p>
            </div>
            <div className="stats">
              <span>{topicCount} 个热点</span>
              <span>{paperCount} 篇论文</span>
              {manifest.generated_at && (
                <span>更新于 {manifest.generated_at.slice(0, 10)}</span>
              )}
            </div>
          </div>
        </section>

        {!hasGraph && !topics.length ? (
          <div className="empty-state">
            <b>当期热点暂未生成</b>
            <span>下一次自动更新会生成新的月度议题。</span>
          </div>
        ) : hasGraph ? (
          <HotspotPageClient
            graph={graph}
            trends={trends}
            manifest={manifest}
            hotspots={hotspots}
            papers={papers}
            byId={byId}
            topics={topics}
          />
        ) : (
          /* Fallback: legacy LLM-only hotspot view */
          <section className="hotspot-feed">
            <div className="section-heading">
              <h2>研究议题</h2>
              <span className="count">{displayPeriod(hotspots?.period_start, hotspots?.period_end)} · 仅基于公开论文</span>
            </div>
            <div className="hotspot-grid">
              {topics.map((topic) => (
                <article className="hotspot-topic" key={topic.title}>
                  <header>
                    <h3>{topic.title}</h3>
                    <p>{topic.description}</p>
                  </header>
                  <div className="hotspot-papers">
                    {(topic.paper_ids || [])
                      .map((id) => byId.get(Number(id)))
                      .filter((paper): paper is Paper => Boolean(paper))
                      .map((paper) => <PaperCard key={paper.id} paper={paper} />)}
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
