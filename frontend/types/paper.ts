/**
 * Shared paper data model. Mirrors the shape of the static JSON snapshots
 * emitted by the backend (`frontend/public/data/papers.json`,
 * `all_papers.json`).
 */
export type Relevance = "High" | "Medium" | "Unrated" | string;

export interface Paper {
  id?: number;
  title?: string;
  /** May be a display string or an array of author names. */
  authors?: string | string[];
  journal?: string;
  published_date?: string;
  source_url?: string;
  doi?: string;
  relevance?: Relevance;
  score?: number | null;
  summary?: string;
  reason?: string;
  tags?: string[];
  volume?: string;
  issue?: string;
}
