"use client";

import { useState, useCallback } from "react";
import { GitFork, ListOrdered, LayoutGrid } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { HotspotNetwork } from "../../components/hotspots/hotspot-network";
import { HotspotDetailPanel } from "../../components/hotspots/hotspot-detail-panel";
import { HotspotTrendTable } from "../../components/hotspots/hotspot-trend-table";
import type {
  GraphData,
  GraphNode,
  TrendItem,
  ManifestData,
  HotspotsData,
  HotspotTopic,
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
}

export function HotspotPageClient({
  graph,
  trends,
  manifest,
  hotspots,
  papers,
  byId,
  topics,
}: HotspotPageClientProps) {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [activeTab, setActiveTab] = useState("graph");

  const handleSelectNode = useCallback((node: GraphNode | null) => {
    setSelectedNode(node);
  }, []);

  const handleSelectTopic = useCallback(
    (topicId: string) => {
      const node = graph.nodes.find((n) => n.id === topicId);
      if (node) {
        setSelectedNode(node);
        setActiveTab("graph");
      }
    },
    [graph.nodes],
  );

  return (
    <Tabs value={activeTab} onValueChange={setActiveTab}>
      <div className="section-heading">
        <h2>研究议题</h2>
        <TabsList>
          <TabsTrigger value="graph">
            <GitFork size={14} />
            热点图谱
          </TabsTrigger>
          <TabsTrigger value="trends">
            <ListOrdered size={14} />
            趋势排行
          </TabsTrigger>
          <TabsTrigger value="overview">
            <LayoutGrid size={14} />
            议题概览
          </TabsTrigger>
        </TabsList>
      </div>

      <TabsContent value="graph">
        <div className="hotspot-graph-layout">
          <div className="hotspot-graph-main">
            <HotspotNetwork
              graph={graph}
              selectedNodeId={selectedNode?.id || null}
              onSelectNode={handleSelectNode}
            />
          </div>
          <HotspotDetailPanel
            node={selectedNode}
            onClose={() => setSelectedNode(null)}
          />
        </div>
      </TabsContent>

      <TabsContent value="trends">
        <HotspotTrendTable trends={trends} onSelectTopic={handleSelectTopic} />
      </TabsContent>

      <TabsContent value="overview">
        {!topics.length ? (
          <div className="empty-state">
            <b>议题概览暂未生成</b>
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
