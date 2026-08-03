import type { HotspotTopic } from "../../types/hotspot";
import type { Paper } from "../../types/paper";
import { getFeaturedPapers, getHotspots, getHotspotGraph, getHotspotTrends, getHotspotManifest, getTopicDetails } from "../../lib/data";
import { HotspotPageClient } from "./page-client";

function asText(value: unknown): string { return Array.isArray(value) ? value.join(" ") : String(value || ""); }
function displayPeriod(start?: string, end?: string): string { return start && end ? `${start.replaceAll("-", ".")} – ${end.replaceAll("-", ".")}` : "近一个月"; }

function PaperCard({ paper }: { paper: Paper }) {
  return <article className="paper-card"><div className="paper-topline"><span className={`badge ${(paper.relevance || "").toLowerCase()}`}>{paper.relevance || "精选"}</span><time>{paper.published_date || "日期待补充"}</time></div>{paper.source_url ? <a className="paper-title" href={paper.source_url} target="_blank" rel="noreferrer">{paper.title}</a> : <h3 className="paper-title">{paper.title}</h3>}<p className="paper-meta">{[asText(paper.authors), paper.journal].filter(Boolean).join(" · ")}</p>{paper.summary && <p className="paper-summary">{paper.summary}</p>}<div className="paper-tags">{(paper.tags || []).map((tag) => <span className="tag" key={tag}>{tag}</span>)}{paper.method && <span className="tag method-tag" title="研究方法">{paper.method}</span>}</div></article>;
}

export default function HotspotsPage() {
  const hotspots = getHotspots();
  const papers = getFeaturedPapers();
  const graph = getHotspotGraph();
  const trends = getHotspotTrends();
  const manifest = getHotspotManifest();

  // `papers` stays server-side: the client only gets the `byId` lookup map
  // it actually renders, not the full array (saves ~290KB of RSC payload).
  const byId = new Map(papers.map((paper) => [Number(paper.id), paper]));
  const topics: HotspotTopic[] = Array.isArray(hotspots?.topics) ? hotspots.topics : [];
  const topicDetails = getTopicDetails();

  const hasGraph = graph.points.length > 0;

  return (
    <div className="main hotspots-main">
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
            byId={byId}
            topics={topics}
            topicDetails={topicDetails}
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
    </div>
  );
}
