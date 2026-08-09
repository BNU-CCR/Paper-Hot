/**
 * Shared paper data model. Mirrors the shape of the static JSON snapshots
 * emitted by the backend (`frontend/public/data/papers.json`,
 * `all_papers.json`).
 */
export type Relevance = "High" | "Medium" | "Unrated" | string;

export interface Paper {
  id?: number;
  title?: string;
  title_zh?: string;
  /** May be a display string or an array of author names. */
  authors?: string | string[];
  /** Deduplicated author affiliations from Crossref / Semantic Scholar. */
  institutions?: string[];
  journal?: string;
  published_date?: string;
  source_url?: string;
  doi?: string;
  relevance?: Relevance;
  score?: number | null;
  /** Original English abstract supplied by the journal index. */
  abstract?: string;
  abstract_zh?: string;
  summary?: string;
  reason?: string;
  tags?: string[];
  /** AI 判定的研究方法标签（质性分析/量化分析/理论分析/综述/计算传播学，可为空）。 */
  method?: string;
  volume?: string;
  issue?: string;
}
