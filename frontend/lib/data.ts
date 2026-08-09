import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import type { HotspotsData, ManifestData, GraphData, TrendItem, TopicDetail } from "../types/hotspot";
import type { Journal } from "../types/journal";
import type { Paper } from "../types/paper";

/**
 * Build-time readers for the static JSON snapshots in `public/data/`.
 *
 * The site is statically exported, so these run once at build time and the
 * result is pre-rendered into HTML — no runtime `fetch` in the browser.
 * Only import this module from server components (pages); pass the data
 * down to client components as props.
 */
const dataDir = path.join(process.cwd(), "public/data");

function readJson<T>(fileName: string, fallback: T): T {
  try {
    return JSON.parse(readFileSync(path.join(dataDir, fileName), "utf8")) as T;
  } catch {
    return fallback;
  }
}

export function getFeaturedPapers(): Paper[] {
  const data = readJson<unknown>("papers.json", []);
  return Array.isArray(data) ? (data as Paper[]).map(pickPaper) : [];
}

export function getAllPapers(): Paper[] {
  const data = readJson<unknown>("all_papers.json", []);
  return Array.isArray(data) ? (data as Paper[]).map(pickPaper) : [];
}

/**
 * Project a raw paper record down to the fields the `Paper` model actually
 * declares. The backend snapshots carry extra bookkeeping columns
 * (`detail_slug`, `tracked_journal`, `source_type`, `screening_status`)
 * that no page renders — dropping them at build time keeps them out of
 * every RSC flight payload (the home page alone ships 600+ papers).
 */
function pickPaper(raw: Paper): Paper {
  const {
    id, title, title_zh, authors, journal, published_date, source_url, doi,
    relevance, score, abstract, abstract_zh, summary, reason, tags, volume, issue, method,
  } = raw;
  const paper: Paper = { id, title, title_zh, authors, journal, published_date, source_url, doi, relevance, score, abstract, abstract_zh, summary, reason, tags, volume, issue, method };
  // Strip `undefined` entries so they don't bloat the serialized payload.
  return Object.fromEntries(Object.entries(paper).filter(([, v]) => v !== undefined)) as Paper;
}

/**
 * Match a paper to a tracked journal, tolerating the name variants the
 * backend snapshots use (comma spacing, the ICONO14 spelling, etc.).
 * Server-side only: pages pre-filter with this so client components receive
 * just the subset they render instead of the whole paper corpus.
 */
export function matchesJournal(paper: Paper, journal: Journal): boolean {
  const aliases = new Set([journal.name, journal.name.replace(", ", " "), journal.name.replace("Revista Icono 14", "Revista ICONO14")]);
  if (journal.name === "Information, Communication & Society") aliases.add("Information Communication & Society");
  return aliases.has(paper.journal ?? "");
}

export function getHotspots(): HotspotsData {
  return readJson<HotspotsData>("hotspots.json", { topics: [] });
}

// ── Hotspot network data ──

/** Build-time: load the hotspot semantic-map graph (normalized shape). */
export function getHotspotGraph(): GraphData {
  const data = readJson<Partial<GraphData>>("hotspots/graph.json", {});
  return {
    schema_version: typeof data.schema_version === "number" ? data.schema_version : 0,
    generated_at: data.generated_at ?? "",
    embedding_model: data.embedding_model ?? "",
    embedding_dimension: data.embedding_dimension ?? 0,
    umap: data.umap ?? { n_neighbors: 0, min_dist: 0, random_state: 0 },
    points: Array.isArray(data.points) ? data.points : [],
    links: Array.isArray(data.links) ? data.links : [],
  };
}

/** Build-time: load the hotspot manifest. */
export function getHotspotManifest(): ManifestData {
  return readJson<ManifestData>("hotspots/manifest.json", {
    schema_version: 0,
    generated_at: "",
    embedding_model: "",
    embedding_dimension: 0,
    period: { recent_start: "", recent_end: "", baseline_start: "", baseline_end: "" },
    paper_count: 0,
    topic_count: 0,
    edge_count: 0,
  });
}

/** Build-time: load the trend ranking. */
export function getHotspotTrends(): TrendItem[] {
  return readJson<TrendItem[]>("hotspots/trends.json", []);
}

/**
 * Build-time: load every per-topic detail file into a map keyed by topic_id.
 *
 * Reading these at build time lets the detail panel render from props
 * instead of runtime `fetch`, which avoids basePath-mismatch 404s on
 * GitHub Pages and keeps the page RSC-first.
 */
export function getTopicDetails(): Record<string, TopicDetail> {
  const dir = path.join(dataDir, "hotspots/topics");
  let files: string[];
  try {
    files = readdirSync(dir);
  } catch {
    return {};
  }
  const map: Record<string, TopicDetail> = {};
  for (const name of files) {
    if (!name.endsWith(".json")) continue;
    const detail = readJson<TopicDetail>(`hotspots/topics/${name}`, {} as TopicDetail);
    if (detail && detail.topic_id) {
      const keywords = Array.isArray(detail.keywords)
        ? detail.keywords
        : String(detail.keywords || "").split(/[,，;；]/).map((item) => item.trim()).filter(Boolean);
      map[detail.topic_id] = { ...detail, keywords };
    }
  }
  return map;
}
