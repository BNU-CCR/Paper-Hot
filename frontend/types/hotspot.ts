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

// ── Semantic map (graph.json, schema v2) ──
/**
 * A point in the semantic map. Paper points are small dots positioned by
 * their UMAP coordinate; topic points are anchors at the cloud centroid
 * that carry the display label and a `detailFile` for the detail panel.
 */
export interface GraphPoint {
  id: string;
  type: "paper" | "topic";
  shape: number; // 0 = circle (paper), 6 = star (topic anchor)
  x: number;
  y: number;
  /** topic group index (pointColorBy / pointClusterBy), -1 = noise */
  topic: number;
  /** stable topic id (or "noise") */
  topicId: string;
  label: string; // non-empty only on topic anchors
  heat: number; // 0-100 (pointSizeBy)
  title?: string;
  paperId?: number;
  paperCount?: number;
  journalCount?: number;
  growth?: number;
  status?: string;
  detailFile?: string;
}

export interface GraphLink {
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
  umap: {
    n_neighbors: number;
    min_dist: number;
    random_state: number;
  };
  points: GraphPoint[];
  links: GraphLink[];
  topics_meta?: {
    topic_id: string;
    cluster_id: number;
    size: number;
    hot_score: number;
    centroid: number[];
    paper_ids: number[];
    x: number;
    y: number;
  }[];
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
