/**
 * Hotspot aggregation data model. Mirrors `frontend/public/data/hotspots.json`.
 */
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
