"use client";

import { useState, useCallback } from "react";
import { ChevronDown, GitFork, LayoutGrid } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { Button } from "../../components/ui/button";
import { HotspotNetwork } from "../../components/hotspots/hotspot-network";
import { HotspotDetailPanel } from "../../components/hotspots/hotspot-detail-panel";
import { HotspotTrendTable } from "../../components/hotspots/hotspot-trend-table";
import type {
  GraphData,
  GraphPoint,
  TrendItem,
  ManifestData,
  HotspotsData,
  HotspotTopic,
  TopicDetail,
} from "../../types/hotspot";
import type { Paper } from "../../types/paper";

function asText(value: unknown): string {
  return Array.isArray(value) ? value.join(" ") : String(value || "");
}

function PaperCard({ paper }: { paper: Paper }) {
  return (
    <article className="paper-card">
      <div className="paper-topline">
        <span className={`badge ${(paper.relevance || "").toLowerCase()}`}>
          {paper.relevance || "精选"}
        </span>
        <time>{paper.published_date || "日期待补充"}</time>
      </div>
      {paper.source_url ? (
        <a className="paper-title" href={paper.source_url} target="_blank" rel="noreferrer">
          {paper.title}
        </a>
      ) : (
        <h3 className="paper-title">{paper.title}</h3>
      )}
      <p className="paper-meta">
        {[asText(paper.authors), paper.journal].filter(Boolean).join(" · ")}
      </p>
      {paper.summary && <p className="paper-summary">{paper.summary}</p>}
      <div className="paper-tags">
        {(paper.tags || []).map((tag) => (
          <span className="tag" key={tag}>
            {tag}
          </span>
        ))}
      </div>
    </article>
  );
}

interface HotspotPageClientProps {
  graph: GraphData;
  trends: TrendItem[];
  manifest: ManifestData;
  hotspots: HotspotsData;
  papers: Paper[];
  byId: Map<number, Paper>;
  topics: HotspotTopic[];
  topicDetails: Record<string, TopicDetail>;
}

export function HotspotPageClient({
  graph,
  trends,
  manifest,
  hotspots,
  papers,
  byId,
  topics,
  topicDetails,
}: HotspotPageClientProps) {
  const [selectedNode, setSelectedNode] = useState<GraphPoint | null>(null);
  const [activeTab, setActiveTab] = useState("graph");
  const [trendExpanded, setTrendExpanded] = useState(false);

  const handleSelectNode = useCallback((node: GraphPoint | null) => {
    setSelectedNode(node);
  }, []);

  const handleSelectTopic = useCallback(
    (topicId: string) => {
      const point = graph.points.find((p) => p.type === "topic" && p.id === topicId);
      if (point) {
        setSelectedNode(point);
        setActiveTab("graph");
      }
    },
    [graph.points],
  );

  return (
    <Tabs value={activeTab} onValueChange={setActiveTab} className="hotspot-tabs">
      <TabsList
        variant="line"
        className="flex-none self-center border-b border-border px-0 mb-[5px]"
      >
        <TabsTrigger value="graph">
          <GitFork size={14} aria-hidden="true" />
          热点图谱
        </TabsTrigger>
        <TabsTrigger value="overview">
          <LayoutGrid size={14} aria-hidden="true" />
          议题推荐
        </TabsTrigger>
      </TabsList>

      <TabsContent value="graph" className="hotspot-workspace">
        <aside className={trendExpanded ? "trend-sidebar expanded" : "trend-sidebar"}>
          <div className="trend-sidebar-header">
            <h3>趋势排行</h3>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="trend-toggle"
              aria-expanded={trendExpanded}
              onClick={() => setTrendExpanded((v) => !v)}
            >
              <ChevronDown size={14} className={trendExpanded ? "chevron-icon open" : "chevron-icon"} />
              趋势详情
            </Button>
          </div>
          <HotspotTrendTable
            trends={trends}
            onSelectTopic={handleSelectTopic}
            selectedTopicId={selectedNode?.id || null}
          />
        </aside>
        <div className="hotspot-map-area">
          <HotspotNetwork
            graph={graph}
            selectedNodeId={selectedNode?.id || null}
            onSelectNode={handleSelectNode}
          />
          <HotspotDetailPanel
            node={selectedNode}
            topicDetails={topicDetails}
            onClose={() => setSelectedNode(null)}
          />
        </div>
      </TabsContent>

      <TabsContent value="overview" className="hotspot-overview">
        {!topics.length ? (
          <div className="empty-state">
            <b>议题推荐暂未生成</b>
            <span>当期热点议题将在此显示。</span>
          </div>
        ) : (
          <section className="hotspot-feed">
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
                      .map((paper) => (
                        <PaperCard key={paper.id} paper={paper} />
                      ))}
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}
      </TabsContent>
    </Tabs>
  );
}
