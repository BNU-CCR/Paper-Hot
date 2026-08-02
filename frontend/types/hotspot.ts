/**
 * Hotspot data models for the network graph, trends, and topic detail views.
 */

// ── Legacy hotspots.json (LLM-generated, kept for overview tab) ──
export interface HotspotTopic {
  title: string;
  description: string;
  paper_ids: number[];
}

export interface HotspotsData {
  topics: HotspotTopic[];
  source_paper_count?: number;
  period_start?: string;
  period_end?: string;
}

// ── Network graph (graph.json) ──
export interface GraphNode {
  id: string;
  label: string;
  x: number;
  y: number;
  size: number;
  hotScore: number;
  growth: number;
  recentCount: number;
  paperCount: number;
  journalCount: number;
  status: string;
  detailFile: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  weight: number;
  width: number;
  opacity: number;
}

export interface GraphData {
  schema_version: number;
  generated_at: string;
  embedding_model: string;
  embedding_dimension: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ── Manifest (manifest.json) ──
export interface ManifestData {
  schema_version: number;
  generated_at: string;
  embedding_model: string;
  embedding_dimension: number;
  period: {
    recent_start: string;
    recent_end: string;
    baseline_start: string;
    baseline_end: string;
  };
  paper_count: number;
  topic_count: number;
  edge_count: number;
}

// ── Trends (trends.json) ──
export interface TrendItem {
  topic_id: string;
  label: string;
  hot_score: number;
  growth: number;
  recent_count: number;
  baseline_count: number;
  journal_count: number;
  lineage_status: string;
  is_hot: boolean;
}

// ── Topic detail (topics/<id>.json) ──
export interface TopicDetailPaper {
  id: number;
  title: string;
  journal: string;
  published_date: string;
  summary: string;
}

export interface TopicDetail {
  topic_id: string;
  label: string;
  description: string;
  why_hot: string;
  hot_score: number;
  growth: number;
  recent_count: number;
  baseline_count: number;
  journal_count: number;
  lineage_status: string;
  keywords: string[];
  papers: TopicDetailPaper[];
}
